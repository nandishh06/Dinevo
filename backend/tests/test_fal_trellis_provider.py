"""FalTrellisProvider tests — no live fal.ai, only request construction and
status mapping against a fake urllib."""

from __future__ import annotations

import json

import pytest

from app.providers.base import ProviderTaskStatus
from app.providers.fal_trellis import FalTrellisProvider, _extract_glb_url


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


def _patch_urlopen(monkeypatch, payload: dict):
    calls: list[dict] = []

    def fake_urlopen(req, timeout=120):
        calls.append(
            {
                "url": req.full_url,
                "method": req.get_method(),
                "body": json.loads(req.data.decode()) if req.data else None,
                "headers": dict(req.headers),
            }
        )
        return _FakeResponse(payload)

    monkeypatch.setattr("app.providers.fal_trellis.urllib.request.urlopen", fake_urlopen)
    return calls


def test_submit_posts_image_url_and_returns_request_id(monkeypatch):
    calls = _patch_urlopen(monkeypatch, {"request_id": "req-123"})
    provider = FalTrellisProvider(api_key="test-key")

    task_id = provider.submit("https://example.com/dish.jpg")

    assert task_id == "req-123"
    assert calls[0]["url"] == "https://queue.fal.run/fal-ai/trellis"
    assert calls[0]["method"] == "POST"
    assert calls[0]["body"] == {"image_url": "https://example.com/dish.jpg"}
    assert calls[0]["headers"]["Authorization"] == "Key test-key"


def test_submit_missing_request_id_raises(monkeypatch):
    _patch_urlopen(monkeypatch, {"no": "request_id"})
    provider = FalTrellisProvider(api_key="test-key")
    with pytest.raises(RuntimeError, match="no request_id"):
        provider.submit("https://example.com/dish.jpg")


def test_poll_maps_fal_statuses(monkeypatch):
    _patch_urlopen(monkeypatch, {"status": "IN_PROGRESS", "progress": 42})
    provider = FalTrellisProvider(api_key="test-key")

    task = provider.poll("req-123")

    assert task.status == "PROCESSING"
    assert task.progress == 42


def test_poll_unknown_status_defaults_to_processing(monkeypatch):
    _patch_urlopen(monkeypatch, {"status": "SOMETHING_ELSE"})
    provider = FalTrellisProvider(api_key="test-key")
    assert provider.poll("req-123").status == "PROCESSING"


def test_fetch_assets_extracts_model_mesh_url(monkeypatch):
    _patch_urlopen(monkeypatch, {"model_mesh": {"url": "https://fal.delivery/mesh.glb"}})
    provider = FalTrellisProvider(api_key="test-key")

    assets = provider.fetch_assets("req-123")

    assert assets.glb_url == "https://fal.delivery/mesh.glb"
    assert assets.usdz_url is None


def test_fetch_assets_missing_mesh_raises(monkeypatch):
    _patch_urlopen(monkeypatch, {"model_mesh": {}})
    provider = FalTrellisProvider(api_key="test-key")
    with pytest.raises(RuntimeError, match="no model_mesh"):
        provider.fetch_assets("req-123")


def test_missing_fal_key_raises(monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    with pytest.raises(RuntimeError, match="FAL_KEY"):
        FalTrellisProvider(api_key="")


def test_extract_glb_url_falls_back_to_other_keys():
    assert _extract_glb_url({"gaussian": {"url": "https://x.glb"}}) == "https://x.glb"
    assert _extract_glb_url({"radiance_field": {"url": "https://y.glb"}}) == "https://y.glb"
    assert _extract_glb_url({"model_mesh": {"url": "https://z.glb"}}) == "https://z.glb"
    assert _extract_glb_url({}) is None


# ---------------------------------------------------------------------------
# Provider selection (fal vs meshy vs trellis)
# ---------------------------------------------------------------------------

def _settings(**overrides) -> "object":
    from app.config import Settings

    defaults = {
        "meshy_api_key": "",
        "fal_key": "",
        "image_to_3d_provider": "fal",
        "trellis_job_dir": "./data/trellis/jobs",
        "trellis_staging_dir": "./data/trellis/staging",
        "trellis_results_dir": "./data/trellis/results",
        "supabase_url": "",
        "supabase_service_role_key": "",
        "supabase_jwt_secret": "",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_build_provider_selects_fal():
    from app.workers import build_provider

    provider = build_provider(_settings(image_to_3d_provider="fal", fal_key="k"))
    assert isinstance(provider, FalTrellisProvider)


def test_build_provider_selects_meshy():
    from app.providers.meshy import MeshyProvider
    from app.workers import build_provider

    provider = build_provider(_settings(image_to_3d_provider="meshy", meshy_api_key="k"))
    assert isinstance(provider, MeshyProvider)


def test_build_provider_selects_trellis():
    from app.providers.local_trellis import LocalTrellisProvider
    from app.workers import build_provider

    provider = build_provider(_settings(image_to_3d_provider="trellis"))
    assert isinstance(provider, LocalTrellisProvider)
