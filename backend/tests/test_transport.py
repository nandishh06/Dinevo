"""Transport-specific tests for the staged Mac <-> Colab job-directory bridge.

These verify the staged transport (submit -> staging/, worker writes to a
shared job dir, Mac reads from results/) WITHOUT Google credentials, a Colab
runtime, or a GPU. They simulate the bridge by moving job dirs between the
staging and results locations exactly as Drive sync would.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.providers.trellis_jobs import (
    JOB_PENDING,
    JOB_PROCESSING,
    JOB_SUCCEEDED,
    JobNotFoundError,
    TrellisJobClient,
)
from tests.conftest import make_real_glb_bytes


@pytest.fixture()
def job_root(tmp_path: Path) -> Path:
    return tmp_path / "trellis_jobs"


def test_submit_writes_to_staging(job_root: Path) -> None:
    client = TrellisJobClient(job_root)
    handle = client.submit("http://testserver/assets/originals/dish_001/x.jpg")

    staging_job = job_root / "staging" / handle.job_id
    assert staging_job.is_dir()
    assert (staging_job / "request.json").exists()
    assert (staging_job / "status.json").exists()
    assert client.poll(handle.job_id).status == JOB_PENDING


def test_poll_falls_back_to_staging_before_results(job_root: Path) -> None:
    client = TrellisJobClient(job_root)
    handle = client.submit("http://testserver/assets/originals/dish_001/x.jpg")

    # Job is in staging; poll must find it.
    assert client.poll(handle.job_id).status == JOB_PENDING


def test_worker_result_in_results_is_authoritative(job_root: Path) -> None:
    """Once the sync moves a completed job into results/, poll+fetch use it
    (results wins over the stale staging copy)."""
    client = TrellisJobClient(job_root)
    handle = client.submit("http://testserver/assets/originals/dish_001/x.jpg")

    # Simulate the Colab worker + Drive sync: move the staged job dir into
    # results/ and write worker outputs there.
    results_job = job_root / "results" / handle.job_id
    shutil.move(str(job_root / "staging" / handle.job_id), str(results_job))
    (results_job / "model.glb").write_bytes(make_real_glb_bytes())
    (results_job / "status.json").write_text(
        json.dumps({"status": JOB_SUCCEEDED, "progress": 100, "error": None}),
        encoding="utf-8",
    )

    assert client.poll(handle.job_id).status == JOB_SUCCEEDED
    assets = client.fetch_assets(handle.job_id)
    assert assets.glb_path is not None and assets.glb_path.exists()
    assert assets.glb_path == results_job / "model.glb"


def test_fetch_assets_missing_job_raises(job_root: Path) -> None:
    client = TrellisJobClient(job_root)
    with pytest.raises(JobNotFoundError):
        client.fetch_assets("job_does_not_exist")


def test_transport_requires_no_credentials() -> None:
    """The staged transport is pure local filesystem — no Google auth, no
    env secrets, no network. Guards against accidental credential coupling."""
    import inspect

    from app.providers import trellis_jobs

    src = inspect.getsource(trellis_jobs)
    for banned in ("google.auth", "credentials", "oauth", "gdrive", "pydrive"):
        assert banned not in src, f"transport must not reference {banned}"


def test_provider_works_with_staged_transport(
    job_root: Path, tmp_path: Path
) -> None:
    """LocalTrellisProvider end-to-end through the staged transport with a
    simulated bridge: submit -> staging, move to results with worker output,
    provider.fetch_assets returns the GLB URL."""
    from app.providers.local_trellis import LocalTrellisProvider

    provider = LocalTrellisProvider(job_root=job_root)
    task_id = provider.submit("http://testserver/assets/originals/dish_001/x.jpg")

    # Simulate worker + sync.
    results_job = job_root / "results" / task_id
    shutil.move(str(job_root / "staging" / task_id), str(results_job))
    (results_job / "model.glb").write_bytes(make_real_glb_bytes())
    (results_job / "status.json").write_text(
        json.dumps({"status": JOB_SUCCEEDED, "progress": 100, "error": None}),
        encoding="utf-8",
    )

    assets = provider.fetch_assets(task_id)
    assert assets.glb_url.endswith(".glb")
    assert assets.usdz_url is None  # no usdz written in this scenario
