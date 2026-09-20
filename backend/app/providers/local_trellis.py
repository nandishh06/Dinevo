"""LocalTrellisProvider — a TRELLIS image->3D implementation of
ImageTo3DProvider that runs the GPU work OUTSIDE the FastAPI process.

The Mac backend never imports the TRELLIS GPU stack (torch and friends).
Instead this provider talks to a TRELLIS worker through the job
protocol in app.providers.trellis_jobs (a shared job-directory transport
today, pointing at the Colab T4 volume; swappable for a network transport
later).

Flow:
  submit(image_url)      -> write job request -> job id (provider_task_id)
  poll(task_id)          -> read worker status.json (PENDING/PROCESSING/...)
  fetch_assets(task_id)  -> return ProviderAsset with GLB/USDZ/preview URLs

GenerationService downloads those URLs into its work dir, validates, and
stores them through AssetStorage — the existing lifecycle is untouched.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.providers.base import (
    ImageTo3DProvider,
    ProviderAsset,
    ProviderTaskStatus,
)
from app.providers.trellis_jobs import (
    JOB_FAILED,
    JOB_PROCESSING,
    JOB_PENDING,
    JOB_SUCCEEDED,
    JobNotFoundError,
    TrellisJobClient,
)

_JOB_STATUS_TO_PROVIDER = {
    JOB_PENDING: "PENDING",
    JOB_PROCESSING: "PROCESSING",
    JOB_SUCCEEDED: "SUCCEEDED",
    JOB_FAILED: "FAILED",
}


class LocalTrellisProvider(ImageTo3DProvider):
    name = "trellis"

    def __init__(
        self,
        job_root: str | os.PathLike[str] | None = None,
        job_client: TrellisJobClient | None = None,
    ) -> None:
        # Injectable client for tests; otherwise build from config env.
        if job_client is not None:
            self._client = job_client
        else:
            root = job_root or os.environ.get(
                "TRELLIS_JOB_DIR", str(Path("./data/trellis_jobs").resolve())
            )
            self._client = TrellisJobClient(Path(root))

    # -- ImageTo3DProvider -------------------------------------------------

    def submit(self, image_url: str) -> str:
        handle = self._client.submit(image_url)
        return handle.job_id

    def poll(self, task_id: str) -> ProviderTaskStatus:
        status = self._client.poll(task_id)
        return ProviderTaskStatus(
            status=_JOB_STATUS_TO_PROVIDER.get(status.status, "PENDING"),
            progress=status.progress,
            error=status.error,
        )

    def fetch_assets(self, task_id: str) -> ProviderAsset:
        handle = self._client.fetch_assets(task_id)
        if handle.status != JOB_SUCCEEDED:
            raise RuntimeError(
                f"TRELLIS job {task_id} not succeeded (status={handle.status})"
            )
        if handle.glb_path is None or not handle.glb_path.exists():
            raise RuntimeError(f"TRELLIS job {task_id} produced no GLB")

        previews = {}
        for png in handle.preview_paths:
            previews[png.stem.replace("preview_", "")] = png.as_uri()

        return ProviderAsset(
            glb_url=handle.glb_path.as_uri(),
            usdz_url=(
                handle.usdz_path.as_uri() if handle.usdz_path and handle.usdz_path.exists() else None
            ),
            preview_urls=previews or None,
        )
