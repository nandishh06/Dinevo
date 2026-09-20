"""Tests for Supabase JWT verification and owner-scoped DashboardService.

Tenant isolation is asserted at the service layer (defense-in-depth on top of
RLS): every DashboardService operation scopes by the server-verified owner id,
so one owner can never read or mutate another owner's restaurant/category/item.

These tests use a fake Supabase client — no live Supabase or network required.
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.services.dashboard_service import DashboardService
from app.supabase import (
    SupabaseNotConfigured,
    get_authenticated_user_id,
    verify_supabase_jwt,
)
from tests.fake_supabase import FakeSupabase, seed_restaurant

TEST_SECRET = "test-supabase-jwt-secret-that-is-long-enough-1234567890"


def make_token(sub: str, *, secret: str = TEST_SECRET, expired: bool = False) -> str:
    exp = int(time.time()) - 10 if expired else int(time.time()) + 3600
    return jwt.encode(
        {"sub": sub, "aud": "authenticated", "exp": exp},
        secret,
        algorithm="HS256",
    )


# ---------------------------------------------------------------------------
# JWT verification
# ---------------------------------------------------------------------------

def test_verify_valid_token_returns_sub(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    assert verify_supabase_jwt(make_token("user-123")) == "user-123"


def test_verify_rejects_wrong_secret(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    token = make_token("user-123", secret="a-totally-different-secret-key-1234567890")
    with pytest.raises(jwt.PyJWTError):
        verify_supabase_jwt(token)


def test_verify_rejects_expired(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    with pytest.raises(jwt.PyJWTError):
        verify_supabase_jwt(make_token("user-123", expired=True))


def test_verify_rejects_wrong_audience(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    token = jwt.encode(
        {"sub": "user-123", "aud": "other", "exp": int(time.time()) + 3600},
        TEST_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(jwt.PyJWTError):
        verify_supabase_jwt(token)


def test_verify_requires_secret(monkeypatch):
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    with pytest.raises(SupabaseNotConfigured):
        verify_supabase_jwt(make_token("user-123"))


# ---------------------------------------------------------------------------
# Auth dependency (401 behaviour)
# ---------------------------------------------------------------------------

def _protected_app(secret: str):
    app = FastAPI()

    @app.get("/me")
    def me(user_id: str = Depends(get_authenticated_user_id)) -> dict:
        return {"user_id": user_id}

    return app


def test_auth_dependency_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    client = TestClient(_protected_app(TEST_SECRET))
    res = client.get("/me")
    assert res.status_code == 401


def test_auth_dependency_rejects_invalid_token(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    client = TestClient(_protected_app(TEST_SECRET))
    res = client.get("/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401


def test_auth_dependency_returns_user_id_for_valid_token(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    client = TestClient(_protected_app(TEST_SECRET))
    res = client.get("/me", headers={"Authorization": f"Bearer {make_token('user-123')}"})
    assert res.status_code == 200
    assert res.json()["user_id"] == "user-123"


# ---------------------------------------------------------------------------
# DashboardService tenant isolation
# ---------------------------------------------------------------------------

def _service() -> tuple[DashboardService, FakeSupabase]:
    fake = FakeSupabase()
    return DashboardService(fake), fake


def test_owner_cannot_read_other_owners_restaurant():
    service, fake = _service()
    seed_restaurant(fake, restaurant_id="ra", owner_id="owner-a", name="Restaurant A")
    seed_restaurant(fake, restaurant_id="rb", owner_id="owner-b", name="Restaurant B")

    assert service.get_restaurant("owner-a")["id"] == "ra"
    assert service.get_restaurant("owner-b")["id"] == "rb"


def test_owner_cannot_update_other_owners_restaurant():
    service, fake = _service()
    seed_restaurant(fake, restaurant_id="ra", owner_id="owner-a", name="Restaurant A")
    seed_restaurant(fake, restaurant_id="rb", owner_id="owner-b", name="Restaurant B")

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        service.update_restaurant("owner-a", "rb", {"name": "hacked"})
    assert exc.value.status_code == 404
    # Owner A's own restaurant is unaffected.
    assert service.get_restaurant("owner-b")["name"] == "Restaurant B"


def test_owner_cannot_delete_other_owners_menu_item():
    service, fake = _service()
    seed_restaurant(fake, restaurant_id="ra", owner_id="owner-a")
    seed_restaurant(fake, restaurant_id="rb", owner_id="owner-b")

    item = fake.table("menu_items").insert(
        {"id": "item-b", "restaurant_id": "rb", "name": "Owner B item"}
    ).execute().data[0]

    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        service.delete_menu_item("owner-a", item["id"])
    # Item still exists.
    assert len(fake.table("menu_items").select("*").execute().data) == 1


def test_owner_scoped_crud_roundtrip():
    service, fake = _service()
    seed_restaurant(fake, restaurant_id="ra", owner_id="owner-a", name="Restaurant A")

    category = service.create_category("owner-a", "ra", name="Starters")
    item = service.create_menu_item(
        "owner-a",
        "ra",
        {"category_id": category["id"], "name": "Paneer Tikka", "price": 249},
    )

    assert service.list_categories("owner-a", "ra")[0]["name"] == "Starters"
    items = service.list_menu_items("owner-a", "ra")
    assert items[0]["name"] == "Paneer Tikka"

    service.update_menu_item("owner-a", item["id"], {"price": 279})
    assert service.list_menu_items("owner-a", "ra")[0]["price"] == 279

    service.delete_menu_item("owner-a", item["id"])
    assert service.list_menu_items("owner-a", "ra") == []


def test_upload_menu_item_image_stores_and_updates_url():
    service, fake = _service()
    seed_restaurant(fake, restaurant_id="ra", owner_id="owner-a")
    item = service.create_menu_item("owner-a", "ra", {"name": "Biryani", "price": 299})

    url = service.upload_menu_item_image(
        "owner-a", item["id"], data=b"fake-image-bytes", content_type="image/jpeg"
    )
    assert url.startswith("https://storage.test/object/public/restaurant-assets/")
    assert service.list_menu_items("owner-a", "ra")[0]["image_url"] == url
