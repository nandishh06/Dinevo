"""LocalTrellisProvider + job-protocol tests.

All tests run WITHOUT a GPU or TRELLIS: they use the pure-stdlib job protocol
and fake the worker by writing job files directly. The provider never imports
torch/TRELLIS/kaolin/xformers (verified by test).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from app.config import load_settings
from app.providers.base import ImageTo3DProvider
from app.providers.local_trellis import LocalTrellisProvider
from app.providers.trellis_jobs import (
    JOB_FAILED,
    JOB_PROCESSING,
    JOB_SUCCEEDED,
    TrellisJobClient,
)
from app.workers import build_provider
from tests.conftest import make_real_glb_bytes


@pytest.fixture()
def job_root(tmp_path: Path) -> Path:
    return tmp_path / "jobs"


@pytest.fixture()
def provider(job_root: Path) -> LocalTrellisProvider:
    return LocalTrellisProvider(job_root=job_root)


def _seed(job_root: Path, *, status: str = JOB_SUCCEEDED, with_usdz: bool = True):
    """Submit a job via the client, then simulate the worker by writing job
    files + a local GLB/USDZ the provider will hand back as file:// URLs."""
    client = TrellisJobClient(job_root)
    handle = client.submit("http://testserver/assets/originals/dish_001/x.jpg")
    job_dir = job_root / "staging" / handle.job_id

    # Simulate worker output + Drive sync back into results/.
    results_job = job_root / "results" / handle.job_id
    results_job.mkdir(parents=True, exist_ok=True)
    (results_job / "model.glb").write_bytes(make_real_glb_bytes())
    if with_usdz:
        (results_job / "model.usdz").write_bytes(b"usdz-bytes")
    (results_job / "status.json").write_text(
        json.dumps({"status": status, "progress": 100, "error": None}),
        encoding="utf-8",
    )
    return handle.job_id, results_job


def _complete_job(job_root: Path, task_id: str, *, status: str = JOB_SUCCEEDED) -> None:
    """Write worker outputs into the job dir the provider's submit() created
    (under staging/), then move it to results/ as the sync would."""
    job_dir = job_root / "staging" / task_id
    (job_dir / "model.glb").write_bytes(make_real_glb_bytes())
    (job_dir / "model.usdz").write_bytes(b"usdz-bytes")
    (job_dir / "status.json").write_text(
        json.dumps({"status": status, "progress": 100, "error": None}),
        encoding="utf-8",
    )
    shutil.move(str(job_dir), str(job_root / "results" / task_id))


# -- interface + isolation ---------------------------------------------------


def test_provider_satisfies_abstraction(provider: LocalTrellisProvider) -> None:
    assert isinstance(provider, ImageTo3DProvider)
    assert provider.name == "trellis"


def test_provider_does_not_import_gpu_deps() -> None:
    """The provider module (and its imports) must never pull torch/TRELLIS."""
    import inspect

    from app.providers import local_trellis, trellis_jobs

    for mod in (local_trellis, trellis_jobs):
        src = inspect.getsource(mod)
        for banned in ("import torch", "from torch", "import trellis", "from trellis", "kaolin", "xformers"):
            assert banned not in src, f"{mod.__name__} must not reference {banned}"


def test_backend_importable_without_torch(job_root: Path, monkeypatch) -> None:
    """Backend imports fine when torch/TRELLIS are absent (they are, on the
    Mac venv). Guards against accidental import-time GPU deps."""
    monkeypatch.setenv("IMAGE_TO_3D_PROVIDER", "trellis")
    monkeypatch.setenv("TRELLIS_JOB_DIR", str(job_root))

    provider = build_provider(load_settings())
    assert provider.name == "trellis"


# -- job protocol + provider unit behavior -----------------------------------


def test_submit_returns_job_id(provider: LocalTrellisProvider, job_root: Path) -> None:
    task_id = provider.submit("http://testserver/assets/originals/dish_001/x.jpg")
    assert task_id.startswith("job_")
    # Job lands in staging/ (the staged transport boundary).
    assert (job_root / "staging" / task_id / "request.json").exists()
    assert (job_root / "staging" / task_id / "status.json").exists()


def test_poll_reflects_worker_status(
    provider: LocalTrellisProvider, job_root: Path
) -> None:
    task_id, job_dir = _seed(job_root, status=JOB_PROCESSING)
    (job_dir / "status.json").write_text(
        json.dumps({"status": JOB_PROCESSING, "progress": 40, "error": None}),
        encoding="utf-8",
    )
    status = provider.poll(task_id)
    assert status.status == "PROCESSING"
    assert status.progress == 40


def test_fetch_assets_returns_glb_usdz_previews(
    provider: LocalTrellisProvider, job_root: Path
) -> None:
    task_id, job_dir = _seed(job_root)
    (job_dir / "previews").mkdir(exist_ok=True)
    (job_dir / "previews" / "preview_front.png").write_bytes(b"png")

    assets = provider.fetch_assets(task_id)
    assert assets.glb_url.endswith(".glb")
    assert assets.usdz_url is not None and assets.usdz_url.endswith(".usdz")
    assert assets.preview_urls is not None and "front" in assets.preview_urls


def test_fetch_assets_requires_success(
    provider: LocalTrellisProvider, job_root: Path
) -> None:
    task_id, _ = _seed(job_root, status=JOB_FAILED)
    with pytest.raises(RuntimeError, match="not succeeded"):
        provider.fetch_assets(task_id)


def test_no_gpu_invocation() -> None:
    """The normal suite never touches CUDA: LocalTrellisProvider and the job
    protocol are pure-stdlib. Importing the provider must not pull torch or
    any TRELLIS GPU module into sys.modules."""
    import app.providers.local_trellis as lt
    import app.providers.trellis_jobs as tj

    gpu_roots = {"torch", "trellis", "kaolin", "xformers"}
    assert not any(
        m.split(".")[0] in gpu_roots for m in sys.modules
    ), "provider import pulled in a GPU dependency"

    import inspect

    for mod in (lt, tj):
        src = inspect.getsource(mod)
        for banned in ("import torch", "from torch", "import trellis", "from trellis"):
            assert banned not in src, f"{mod.__name__} must not reference {banned}"
