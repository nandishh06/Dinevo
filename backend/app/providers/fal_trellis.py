"""FalTrellisProvider — fal.ai TRELLIS image->3D implementation of
ImageTo3DProvider.

Uses fal.ai's asynchronous queue API over plain HTTP (stdlib only, no SDK):

  POST   https://queue.fal.run/fal-ai/trellis            -> {"request_id": ...}
  GET    .../requests/{request_id}/status                -> {"status": ...}
  GET    .../requests/{request_id}                       -> {"model_mesh": {"url": ...}}

FAL_KEY is read from the environment (or injected for tests). It must never be
exposed to the frontend; this provider runs server-side only.
"""

from __future__ import annotations

import json
import os
import urllib.request
from urllib.error import HTTPError, URLError

from app.providers.base import (
    ImageTo3DProvider,
    ProviderAsset,
    ProviderTaskStatus,
)

FAL_QUEUE_BASE = "https://queue.fal.run"
FAL_TRELLIS_MODEL = "fal-ai/trellis"

# fal.ai queue status -> provider status (the ImageTo3DProvider contract).
_FAL_STATUS_TO_PROVIDER = {
    "IN_QUEUE": "PENDING",
    "IN_PROGRESS": "PROCESSING",
    "COMPLETED": "SUCCEEDED",
}


class FalTrellisProvider(ImageTo3DProvider):
    name = "fal"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("FAL_KEY", "")
        if not self._api_key:
            raise RuntimeError("FAL_KEY is not set")

    # -- ImageTo3DProvider -------------------------------------------------

    def submit(self, image_url: str) -> str:
        payload = {"image_url": image_url}
        task = self._request(
            "POST", f"{FAL_QUEUE_BASE}/{FAL_TRELLIS_MODEL}", body=payload
        )
        request_id = task.get("request_id")
        if not request_id:
            raise RuntimeError(f"fal.ai submit returned no request_id: {task!r}")
        return str(request_id)

    def poll(self, task_id: str) -> ProviderTaskStatus:
        task = self._request(
            "GET", f"{FAL_QUEUE_BASE}/{FAL_TRELLIS_MODEL}/requests/{task_id}/status"
        )
        raw_status = str(task.get("status", "IN_QUEUE"))
        status = _FAL_STATUS_TO_PROVIDER.get(raw_status, "PROCESSING")
        # fal.ai does not expose a percentage for TRELLIS; only surface real
        # progress when the provider actually returns it.
        progress = int(task.get("progress", 0) or 0)
        return ProviderTaskStatus(status=status, progress=progress)

    def fetch_assets(self, task_id: str) -> ProviderAsset:
        task = self._request(
            "GET", f"{FAL_QUEUE_BASE}/{FAL_TRELLIS_MODEL}/requests/{task_id}"
        )
        glb_url = _extract_glb_url(task)
        if not glb_url:
            raise RuntimeError(f"fal.ai task {task_id} returned no model_mesh URL")
        return ProviderAsset(glb_url=glb_url, usdz_url=None, preview_urls=None)

    # -- internals ---------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        body: dict | None = None,
        timeout: int = 120,
    ) -> dict:
        headers = {"Authorization": f"Key {self._api_key}"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as exc:
            raise RuntimeError(
                f"fal.ai {method} failed: HTTP {exc.code} {exc.reason}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"fal.ai {method} unreachable: {exc.reason}") from exc


def _extract_glb_url(payload: dict) -> str | None:
    """Best-effort extraction of the GLB URL from a fal.ai TRELLIS result.

    The primary output is `model_mesh.url` (a signed URL to a .glb file).
    """
    for key in ("model_mesh", "gaussian", "radiance_field"):
        value = payload.get(key)
        if isinstance(value, dict) and value.get("url"):
            return str(value["url"])
    return None
