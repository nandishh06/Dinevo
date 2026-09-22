"""RLS tenant-isolation integration tests (require a live Supabase project).

These tests are skipped unless SUPABASE_URL, SUPABASE_ANON_KEY, and
SUPABASE_SECRET_KEY are present. They verify that even a DIRECT Supabase
query with the anon key + a user's JWT cannot cross tenant boundaries — i.e.
the database RLS policies, not application code, enforce isolation.

Run after applying supabase/migrations/0001_saas_foundation.sql:

    cd backend
    set -a && . ./.env && set +a
    .venv/bin/python -m pytest tests/test_rls_integration.py -q
"""

from __future__ import annotations

import os
import uuid

import pytest
from supabase import Client, create_client

pytestmark = pytest.mark.skipif(
    not (
        os.environ.get("SUPABASE_URL")
        and os.environ.get("SUPABASE_ANON_KEY")
        and os.environ.get("SUPABASE_SECRET_KEY")
    ),
    reason="requires live Supabase env (URL + anon + secret key)",
)


def _make_client(anon: bool) -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"] if anon else os.environ["SUPABASE_SECRET_KEY"]
    return create_client(url, key)


def _create_confirmed_user(admin: Client, anon: Client, email: str) -> tuple[str, str]:
    """Create an email-confirmed user and return (user_id, access_token)."""
    password = "test-password-123"
    created = admin.auth.admin.create_user(
        {"email": email, "password": password, "email_confirm": True}
    )
    user_id = created.user.id
    signed_in = anon.auth.sign_in_with_password({"email": email, "password": password})
    session = signed_in.session
    if session is None:
        raise RuntimeError(f"sign_in failed for {email}")
    return user_id, session.access_token


def test_rls_blocks_cross_tenant_access():
    admin = _make_client(anon=False)  # service role: bypasses RLS
    anon = _make_client(anon=True)    # anon: RLS enforced

    tag = uuid.uuid4().hex[:8]
    email_a = f"owner-a-{tag}@gmail.com"
    email_b = f"owner-b-{tag}@gmail.com"

    user_a_id, user_a_token = _create_confirmed_user(admin, anon, email_a)
    user_b_id, user_b_token = _create_confirmed_user(admin, anon, email_b)

    # Seed owner A's restaurant + menu item via the service role (RLS bypassed).
    # owner_id must equal the auth user's UUID (profiles.id).
    ra = (
        admin.table("restaurants")
        .insert({"owner_id": user_a_id, "name": f"A {tag}", "slug": f"a-{tag}"})
        .execute()
        .data[0]
    )
    cat = (
        admin.table("categories")
        .insert({"restaurant_id": ra["id"], "name": "Mains", "sort_order": 0})
        .execute()
        .data[0]
    )
    item = (
        admin.table("menu_items")
        .insert(
            {
                "restaurant_id": ra["id"],
                "category_id": cat["id"],
                "name": "A secret dish",
                "price": 99,
            }
        )
        .execute()
        .data[0]
    )

    # Owner B (anon key + B's JWT) must NOT see Owner A's data.
    anon.postgrest.auth(user_b_token)

    r_visible = anon.table("restaurants").select("*").eq("id", ra["id"]).execute().data
    assert r_visible == [], "RLS leaked restaurant A to owner B"

    c_visible = anon.table("categories").select("*").eq("id", cat["id"]).execute().data
    assert c_visible == [], "RLS leaked category A to owner B"

    i_visible = anon.table("menu_items").select("*").eq("id", item["id"]).execute().data
    assert i_visible == [], "RLS leaked menu item A to owner B"

    # Owner B must not be able to update or delete Owner A's data (0 rows affected).
    anon.table("menu_items").update({"price": 1}).eq("id", item["id"]).execute()
    anon.table("categories").delete().eq("id", cat["id"]).execute()
    still_there = admin.table("menu_items").select("*").eq("id", item["id"]).execute().data
    assert len(still_there) == 1, "RLS allowed owner B to mutate owner A's data"
    assert still_there[0]["price"] == 99, "RLS allowed owner B to change owner A's price"

    # Owner A (anon key + A's JWT) CAN see and update its own data.
    anon.postgrest.auth(user_a_token)
    own = anon.table("restaurants").select("*").eq("id", ra["id"]).execute().data
    assert len(own) == 1, "Owner A should see its own restaurant"

    # Cleanup (service role).
    admin.table("menu_items").delete().eq("id", item["id"]).execute()
    admin.table("categories").delete().eq("id", cat["id"]).execute()
    admin.table("restaurants").delete().eq("id", ra["id"]).execute()
    admin.auth.admin.delete_user(user_a_id)
    admin.auth.admin.delete_user(user_b_id)
