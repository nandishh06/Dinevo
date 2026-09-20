"""SaasGenerationService tests — Supabase-backed image->3D lifecycle.

Uses the in-memory FakeSupabase and FakeImageTo3DProvider. No live Supabase,
no live fal.ai, no network (fake asset server serves file:// URIs).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.providers.base import ProviderAsset
from app.services.dashboard_service import DashboardService
from app.services.saas_generation import SaasGenerationService
from tests.conftest import FakeAssetServer, FakeImageTo3DProvider
from tests.fake_supabase import FakeSupabase, seed_restaurant


def _seed_item(
    fake: FakeSupabase,
    *,
    owner_id: str = "owner-a",
    item_id: str = "item-1",
    image_url: str | None = "https://example.com/dish.jpg",
) -> dict:
    seed_restaurant(fake, restaurant_id="ra", owner_id=owner_id)
    return fake.table("menu_items").insert(
        {
            "id": item_id,
            "restaurant_id": "ra",
            "name": "Biryani",
            "image_url": image_url,
            "price": 299,
        }
    ).execute().data[0]


def _service(fake: FakeSupabase, provider=None) -> SaasGenerationService:
    return SaasGenerationService(fake, provider or FakeImageTo3DProvider())


# ---------------------------------------------------------------------------
# create_generation
# ---------------------------------------------------------------------------

def test_create_generation_sets_generating():
    fake = FakeSupabase()
    _seed_item(fake)
    service = _service(fake)

    gen = service.create_generation("owner-a", "item-1", provider_name="fal")

    assert gen["status"] == "QUEUED"
    assert gen["provider"] == "fal"
    item = fake.table("menu_items").select("*").eq("id", "item-1").execute().data[0]
    assert item["model_status"] == "GENERATING"
    assert item["model_url"] is None


def test_duplicate_active_generation_conflicts():
    fake = FakeSupabase()
    _seed_item(fake)
    service = _service(fake)
    service.create_generation("owner-a", "item-1", provider_name="fal")

    with pytest.raises(HTTPException) as exc:
        service.create_generation("owner-a", "item-1", provider_name="fal")
    assert exc.value.status_code == 409


def test_create_generation_requires_image():
    fake = FakeSupabase()
    _seed_item(fake, image_url=None)
    service = _service(fake)

    with pytest.raises(HTTPException) as exc:
        service.create_generation("owner-a", "item-1", provider_name="fal")
    assert exc.value.status_code == 400


def test_owner_cannot_generate_other_owners_item():
    fake = FakeSupabase()
    _seed_item(fake, owner_id="owner-b")
    service = _service(fake)

    with pytest.raises(HTTPException) as exc:
        service.create_generation("owner-a", "item-1", provider_name="fal")
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# run_generation (worker)
# ---------------------------------------------------------------------------

def test_run_generation_success(fake_asset_server: FakeAssetServer):
    fake = FakeSupabase()
    _seed_item(fake)
    provider = FakeImageTo3DProvider()
    provider.assets = ProviderAsset(glb_url=fake_asset_server.url(fake_asset_server.glb))
    service = SaasGenerationService(fake, provider)

    gen = service.create_generation("owner-a", "item-1", provider_name="fal")
    result = service.run_generation(gen["id"])

    assert result["status"] == "COMPLETED"
    assert result["glb_url"].startswith(
        "https://storage.test/object/public/restaurant-models/"
    )
    item = fake.table("menu_items").select("*").eq("id", "item-1").execute().data[0]
    assert item["model_status"] == "READY"
    assert item["model_url"] == result["glb_url"]


def test_run_generation_failure_marks_failed():
    fake = FakeSupabase()
    _seed_item(fake)
    provider = FakeImageTo3DProvider()
    provider.fail_poll = True
    provider.poll_error = "trellis blew up"
    service = SaasGenerationService(fake, provider)

    gen = service.create_generation("owner-a", "item-1", provider_name="fal")
    result = service.run_generation(gen["id"])

    assert result["status"] == "FAILED"
    assert result["error"] == "trellis blew up"
    item = fake.table("menu_items").select("*").eq("id", "item-1").execute().data[0]
    assert item["model_status"] == "FAILED"
    assert item["model_url"] is None


def test_run_generation_validates_glb(fake_asset_server: FakeAssetServer):
    """A corrupt GLB must FAIL and never publish a model_url."""
    fake_asset_server.glb.write_bytes(b"not a glb at all")

    fake = FakeSupabase()
    _seed_item(fake)
    provider = FakeImageTo3DProvider()
    provider.assets = ProviderAsset(glb_url=fake_asset_server.url(fake_asset_server.glb))
    service = SaasGenerationService(fake, provider)

    gen = service.create_generation("owner-a", "item-1", provider_name="fal")
    result = service.run_generation(gen["id"])

    assert result["status"] == "FAILED"
    assert "validation failed" in (result["error"] or "")
    item = fake.table("menu_items").select("*").eq("id", "item-1").execute().data[0]
    assert item["model_url"] is None
    assert item["model_status"] == "FAILED"


# ---------------------------------------------------------------------------
# get_generation
# ---------------------------------------------------------------------------

def test_get_generation_owner_scoped():
    fake = FakeSupabase()
    _seed_item(fake)
    service = _service(fake)
    service.create_generation("owner-a", "item-1", provider_name="fal")

    gen = service.get_generation("owner-a", "item-1")
    assert gen is not None
    assert gen["menu_item_id"] == "item-1"

    with pytest.raises(HTTPException) as exc:
        service.get_generation("owner-b", "item-1")
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# image replacement invalidation
# ---------------------------------------------------------------------------

def test_image_replacement_invalidates_model():
    fake = FakeSupabase()
    seed_restaurant(fake, restaurant_id="ra", owner_id="owner-a")
    fake.table("menu_items").insert(
        {
            "id": "item-1",
            "restaurant_id": "ra",
            "name": "Biryani",
            "image_url": "https://example.com/old.jpg",
            "model_url": "https://storage.test/old.glb",
            "model_status": "READY",
            "price": 299,
        }
    ).execute()

    service = DashboardService(fake)
    url = service.upload_menu_item_image(
        "owner-a", "item-1", data=b"new-image", content_type="image/jpeg"
    )

    item = fake.table("menu_items").select("*").eq("id", "item-1").execute().data[0]
    assert item["image_url"] == url
    assert item["model_url"] is None
    assert item["model_status"] is None
