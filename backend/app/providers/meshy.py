"""MeshyProvider — Meshy Image-to-3D implementation of ImageTo3DProvider.

Ports the proven API behavior from scripts/m17-meshy-generate.py (the original
CLI experiment, kept as reference). Reused unchanged:

  - the generation profile payload (model_type=standard, ai_model=meshy-7,
    should_texture, enable_pbr, 2k textures, 150k target polycount,
    glb+usdz formats, origin_at=bottom, multi-view thumbnails)
  - Bearer-token auth against api.meshy.ai
  - task creation + polling + asset download shape

Key change from the CLI script: the backend provider receives a stored,
publicly fetchable image URL instead of base64-encoding a local file. Task IDs
are persisted by GenerationService/database, not kept in a CLI loop.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from urllib.error import HTTPError, URLError

from app.providers.base import (
    ImageTo3DProvider,
    ProviderAsset,
    ProviderTaskStatus,
)

MESHY_IMAGE_TO_3D_API = "https://api.meshy.ai/openapi/v1/image-to-3d"

# Generation profile, copied from scripts/m17-meshy-generate.py (PAYLOAD).
_GENERATION_PROFILE = {
    "model_type": "standard",
    "ai_model": "meshy-7",
    "ultra_mode": False,
    "should_texture": True,
    "enable_pbr": True,
    "texture_resolution": "2k",
    "should_remesh": False,
    "target_polycount": 150_000,
    "target_formats": ["glb", "usdz"],
    "multi_view_thumbnails": True,
    "origin_at": "bottom",
}

_POLL_INTERVAL_SECONDS = 10
_MAX_POLL_ATTEMPTS = 60  # ~10 minutes, matches the CLI's patience


class MeshyProvider(ImageTo3DProvider):
    name = "meshy"

    def __init__(self, api_key: str | None = None) -> None:
        # Read from env by default; injectable for tests.
        self._api_key = api_key if api_key is not None else os.environ.get("MESHY_API_KEY", "")
        if not self._api_key:
            raise RuntimeError("MESHY_API_KEY is not set")

    # -- ImageTo3DProvider -------------------------------------------------

    def submit(self, image_url: str) -> str:
        payload = {**_GENERATION_PROFILE, "image_url": image_url}
        task = self._request("POST", MESHY_IMAGE_TO_3D_API, body=payload)
        task_id = task.get("result")
        if not task_id:
            raise RuntimeError(f"Meshy submit returned no task id: {task!r}")
        return str(task_id)

    def poll(self, task_id: str) -> ProviderTaskStatus:
        task = self._request("GET", f"{MESHY_IMAGE_TO_3D_API}/{task_id}")
        status = str(task.get("status", "PENDING"))
        progress = int(task.get("progress", 0) or 0)
        return ProviderTaskStatus(
            status=status,
            progress=progress,
            error=task.get("task_error"),
        )

    def fetch_assets(self, task_id: str) -> ProviderAsset:
        task = self._request("GET", f"{MESHY_IMAGE_TO_3D_API}/{task_id}")
        model_urls = task.get("model_urls", {}) or {}
        glb_url = model_urls.get("glb")
        usdz_url = model_urls.get("usdz")
        if not glb_url:
            raise RuntimeError(f"Meshy task {task_id} returned no glb asset")
        previews = (task.get("thumbnail_urls", {}) or {}) if task.get("thumbnail_urls") else None
        return ProviderAsset(glb_url=str(glb_url), usdz_url=usdz_url and str(usdz_url) or None, preview_urls=previews)

    # -- internals ---------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        body: dict | None = None,
        timeout: int = 60,
    ) -> dict:
        headers = {"Authorization": f"Bearer {self._api_key}"}
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
                f"Meshy API {method} {url} failed: HTTP {exc.code} {exc.reason}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Meshy API {method} {url} unreachable: {exc.reason}"
            ) from exc


def wait_for_provider_task(
    provider: ImageTo3DProvider,
    task_id: str,
    *,
    interval: float = _POLL_INTERVAL_SECONDS,
    max_attempts: int = _MAX_POLL_ATTEMPTS,
) -> ProviderTaskStatus:
    """Blocking poll loop used by the (M2) worker. Kept here so the provider
    module owns its own polling semantics; tests inject a fake provider."""
    for _ in range(max_attempts):
        status = provider.poll(task_id)
        if status.status in ("SUCCEEDED", "FAILED", "CANCELED"):
            return status
        time.sleep(interval)
    return ProviderTaskStatus(status="FAILED", error="Polling timed out")
