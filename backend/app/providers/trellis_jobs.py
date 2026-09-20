"""TRELLIS GPU job protocol — the transport-agnostic boundary between the
Mac backend and the Colab/T4 TRELLIS worker.

This module is PURE STDLIB: it never imports the TRELLIS GPU stack (torch and
friends) or any GPU dependency. It defines a job-directory contract that works
across a shared filesystem (the immediate Colab workflow) and can be swapped
for a network transport later WITHOUT changing GenerationService or the
provider.

Job directory layout (root = config TRELLIS_JOB_DIR):

  <job_id>/request.json        {image_url, params...}   written by backend
  <job_id>/status.json         {"status": PENDING|PROCESSING|SUCCEEDED|FAILED,
                                 "progress": 0-100, "error": null|str}
                               written by the worker
  <job_id>/source.<ext>        locally cached source image (optional)
  <job_id>/model.glb           output (SUCCEEDED)
  <job_id>/model.usdz          optional output
  <job_id>/previews/*.png      optional previews

Status values are the WORKER's provider-level states; GenerationService maps
them onto the generation lifecycle (PENDING/PROCESSING/SUCCEEDED/FAILED).
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError

# Worker-side statuses (provider-level, not the generation lifecycle).
JOB_PENDING = "PENDING"
JOB_PROCESSING = "PROCESSING"
JOB_SUCCEEDED = "SUCCEEDED"
JOB_FAILED = "FAILED"

# Backend-written request fields; the worker MUST NOT trust these blindly.
REQUEST_FIELDS = ("image_url",)


class JobNotFoundError(FileNotFoundError):
    """Raised when a job directory does not exist."""


class JobProtocolError(RuntimeError):
    """Raised on malformed job state (corrupt JSON, invalid status)."""


@dataclass(frozen=True)
class JobStatus:
    status: str
    progress: int = 0
    error: str | None = None


@dataclass
class JobHandle:
    """A job this backend submitted, with its output asset paths."""

    job_id: str
    root: Path
    image_url: str = ""
    status: str = JOB_PENDING
    progress: int = 0
    error: str | None = None
    glb_path: Path | None = None
    usdz_path: Path | None = None
    preview_paths: list[Path] = field(default_factory=list)


def new_job_id() -> str:
    import uuid

    return f"job_{uuid.uuid4().hex}"


class TrellisJobClient:
    """Backend-side client: create jobs, read worker status, fetch outputs.

    Staged file-system transport for the Mac <-> Colab development bridge:

      <job_root>/staging/<job_id>/request.json   written by backend (Mac)
      <job_root>/staging/<job_id>/status.json    PENDING (initial)
      <job_root>/results/<job_id>/status.json    written by Colab worker
      <job_root>/results/<job_id>/model.glb      output (SUCCEEDED)
      <job_root>/results/<job_id>/model.usdz     optional
      <job_root>/results/<job_id>/previews/*.png optional

    The staging/ and results/ directories are the sync boundary: a $0 bridge
    (Google Drive folder mounted on both sides, or rclone/Drive Desktop) moves
    a job dir from staging/ to the shared folder the Colab worker polls, and
    moves the completed job dir back into results/ on the Mac.

    A later network transport implements the same three methods (submit, poll,
    fetch_assets) and nothing else changes.
    """

    def __init__(self, job_root: Path, fetch_timeout: float = 120.0) -> None:
        self.job_root = Path(job_root)
        self.staging_dir = self.job_root / "staging"
        self.results_dir = self.job_root / "results"
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.fetch_timeout = fetch_timeout

    # -- submit ------------------------------------------------------------

    def submit(self, image_url: str) -> JobHandle:
        job_id = new_job_id()
        job_dir = self.staging_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        request = {"image_url": image_url}
        (job_dir / "request.json").write_text(
            json.dumps(request, indent=2), encoding="utf-8"
        )
        (job_dir / "status.json").write_text(
            json.dumps({"status": JOB_PENDING, "progress": 0, "error": None}),
            encoding="utf-8",
        )
        return JobHandle(job_id=job_id, root=job_dir, image_url=image_url)

    # -- poll --------------------------------------------------------------

    def poll(self, job_id: str) -> JobStatus:
        job_dir = self._job_dir(job_id)
        status_file = job_dir / "status.json"
        if not status_file.exists():
            raise JobProtocolError(f"job {job_id}: missing status.json")
        try:
            raw = json.loads(status_file.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise JobProtocolError(f"job {job_id}: corrupt status.json") from exc
        status = str(raw.get("status", JOB_PENDING))
        if status not in (JOB_PENDING, JOB_PROCESSING, JOB_SUCCEEDED, JOB_FAILED):
            raise JobProtocolError(f"job {job_id}: invalid status {status!r}")
        return JobStatus(
            status=status,
            progress=int(raw.get("progress", 0) or 0),
            error=raw.get("error"),
        )

    # -- fetch assets ------------------------------------------------------

    def fetch_assets(self, job_id: str) -> JobHandle:
        job_dir = self._job_dir(job_id)
        status = self.poll(job_id)
        handle = JobHandle(
            job_id=job_id,
            root=job_dir,
            image_url="",
            status=status.status,
            progress=status.progress,
            error=status.error,
        )
        glb = job_dir / "model.glb"
        usdz = job_dir / "model.usdz"
        preview_dir = job_dir / "previews"
        if glb.exists():
            handle.glb_path = glb
        if usdz.exists():
            handle.usdz_path = usdz
        if preview_dir.is_dir():
            handle.preview_paths = sorted(preview_dir.glob("*.png"))
        return handle

    # -- helpers -----------------------------------------------------------

    def _job_dir(self, job_id: str) -> Path:
        """Locate a job in either staging/ or results/ (results wins; the
        worker's output is authoritative)."""
        results_job = self.results_dir / job_id
        if results_job.is_dir():
            return results_job
        staging_job = self.staging_dir / job_id
        if staging_job.is_dir():
            return staging_job
        raise JobNotFoundError(f"job {job_id} not found under {self.job_root}")

    @staticmethod
    def fetch_image_to_local(image_url: str, dest: Path, timeout: float = 120.0) -> Path:
        """Download the stored source image for the worker.

        Used by the worker (and by tests with file:// URLs). The backend
        stores the admin-uploaded image under AssetStorage, so image_url is
        that stored URL — never a local production path.
        """
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(image_url, timeout=timeout) as resp:  # noqa: S310 - configured asset URL
                with dest.open("wb") as out:
                    while True:
                        chunk = resp.read(64 * 1024)
                        if not chunk:
                            break
                        out.write(chunk)
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"failed to fetch source image {image_url}: {exc}") from exc
        if dest.stat().st_size == 0:
            raise RuntimeError(f"source image {image_url} downloaded as empty file")
        return dest
