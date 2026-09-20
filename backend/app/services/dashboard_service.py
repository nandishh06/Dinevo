"""DashboardService — owner-scoped CRUD for the SaaS domain.

Every method receives the SERVER-VERIFIED owner user id and explicitly scopes
queries/mutations to that owner. The Supabase client is the service-role admin
(bypasses RLS), so this explicit scoping is the backend's defense-in-depth on
top of the database RLS policies.

The frontend never supplies an owner_id or a trusted restaurant_id: it supplies
only the authenticated bearer token; this service derives everything else.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import HTTPException, status
from supabase import Client

ASSET_BUCKET = "restaurant-assets"

# Columns the owner may set on a menu item. Never includes restaurant_id,
# image_url, or id (those are server-managed).
_MENU_ITEM_EDITABLE = {
    "category_id",
    "name",
    "description",
    "price",
    "is_available",
    "dietary",
    "ingredients",
    "spice_level",
    "calories",
    "tags",
    "sort_order",
}

_RESTAURANT_EDITABLE = {
    "name",
    "slug",
    "description",
    "address",
    "phone",
    "logo_url",
}


def slugify(name: str) -> str:
    """Deterministic, URL-safe slug from a restaurant name."""
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:60] or f"restaurant-{uuid.uuid4().hex[:8]}"


class DashboardService:
    def __init__(self, supabase: Client) -> None:
        self._db = supabase

    # -- restaurant ---------------------------------------------------------

    def get_restaurant(self, user_id: str) -> dict | None:
        rows = (
            self._db.table("restaurants")
            .select("*")
            .eq("owner_id", user_id)
            .order("created_at")
            .execute()
        )
        return rows.data[0] if rows.data else None

    def create_restaurant(self, user_id: str, *, name: str) -> dict:
        slug = slugify(name)
        rows = (
            self._db.table("restaurants")
            .insert({"owner_id": user_id, "name": name, "slug": slug})
            .execute()
        )
        if not rows.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create restaurant",
            )
        return rows.data[0]

    def update_restaurant(
        self, user_id: str, restaurant_id: str, fields: dict[str, Any]
    ) -> dict:
        self._require_restaurant(user_id, restaurant_id)
        clean = {k: v for k, v in fields.items() if k in _RESTAURANT_EDITABLE and v is not None}
        if not clean:
            # No-op update returns the current row.
            return self._require_restaurant(user_id, restaurant_id)
        rows = (
            self._db.table("restaurants")
            .update(clean)
            .eq("id", restaurant_id)
            .eq("owner_id", user_id)
            .execute()
        )
        if not rows.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
            )
        return rows.data[0]

    # -- categories ---------------------------------------------------------

    def list_categories(self, user_id: str, restaurant_id: str) -> list[dict]:
        self._require_restaurant(user_id, restaurant_id)
        rows = (
            self._db.table("categories")
            .select("*")
            .eq("restaurant_id", restaurant_id)
            .order("sort_order")
            .execute()
        )
        return rows.data or []

    def create_category(
        self,
        user_id: str,
        restaurant_id: str,
        *,
        name: str,
        sort_order: int = 0,
        is_active: bool = True,
    ) -> dict:
        self._require_restaurant(user_id, restaurant_id)
        rows = (
            self._db.table("categories")
            .insert(
                {
                    "restaurant_id": restaurant_id,
                    "name": name,
                    "sort_order": sort_order,
                    "is_active": is_active,
                }
            )
            .execute()
        )
        if not rows.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create category",
            )
        return rows.data[0]

    def update_category(
        self,
        user_id: str,
        category_id: str,
        *,
        name: str | None = None,
        sort_order: int | None = None,
        is_active: bool | None = None,
    ) -> dict:
        self._require_category(user_id, category_id)
        clean = {
            k: v
            for k, v in ({"name": name, "sort_order": sort_order, "is_active": is_active}).items()
            if v is not None
        }
        if not clean:
            return self._require_category(user_id, category_id)
        rows = (
            self._db.table("categories")
            .update(clean)
            .eq("id", category_id)
            .execute()
        )
        if not rows.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )
        return rows.data[0]

    def delete_category(self, user_id: str, category_id: str) -> None:
        self._require_category(user_id, category_id)
        self._db.table("categories").delete().eq("id", category_id).execute()

    # -- menu items ---------------------------------------------------------

    def list_menu_items(self, user_id: str, restaurant_id: str) -> list[dict]:
        self._require_restaurant(user_id, restaurant_id)
        rows = (
            self._db.table("menu_items")
            .select("*")
            .eq("restaurant_id", restaurant_id)
            .order("sort_order")
            .execute()
        )
        return rows.data or []

    def create_menu_item(
        self, user_id: str, restaurant_id: str, fields: dict[str, Any]
    ) -> dict:
        self._require_restaurant(user_id, restaurant_id)
        clean = {k: v for k, v in fields.items() if k in _MENU_ITEM_EDITABLE and v is not None}
        clean["restaurant_id"] = restaurant_id
        if "name" not in clean or not clean["name"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="name is required",
            )
        rows = self._db.table("menu_items").insert(clean).execute()
        if not rows.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create menu item",
            )
        return rows.data[0]

    def update_menu_item(
        self, user_id: str, item_id: str, fields: dict[str, Any]
    ) -> dict:
        self._require_menu_item(user_id, item_id)
        clean = {k: v for k, v in fields.items() if k in _MENU_ITEM_EDITABLE and v is not None}
        if not clean:
            return self._require_menu_item(user_id, item_id)
        rows = self._db.table("menu_items").update(clean).eq("id", item_id).execute()
        if not rows.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found"
            )
        return rows.data[0]

    def delete_menu_item(self, user_id: str, item_id: str) -> None:
        self._require_menu_item(user_id, item_id)
        self._db.table("menu_items").delete().eq("id", item_id).execute()

    # -- image upload -------------------------------------------------------

    def upload_menu_item_image(
        self,
        user_id: str,
        item_id: str,
        *,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload a food image to Supabase Storage and return its public URL.

        Path: restaurants/{restaurant_id}/menu/{item_id}/{uuid}.{ext}
        """
        item = self._require_menu_item(user_id, item_id)
        restaurant_id = item["restaurant_id"]
        ext = _extension_for(content_type)
        path = f"restaurants/{restaurant_id}/menu/{item_id}/{uuid.uuid4().hex}{ext}"
        self._db.storage.from_(ASSET_BUCKET).upload(
            path,
            data,
            {"content-type": content_type},
        )
        public_url = self._db.storage.from_(ASSET_BUCKET).get_public_url(path)
        # A new image invalidates any previously generated model: the old GLB
        # must never be silently associated with the new photograph.
        self._db.table("menu_items").update(
            {"image_url": public_url, "model_url": None, "model_status": None}
        ).eq("id", item_id).execute()
        return public_url

    def upload_restaurant_logo(
        self,
        user_id: str,
        restaurant_id: str,
        *,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload a restaurant logo to Supabase Storage and return its public URL."""
        self._require_restaurant(user_id, restaurant_id)
        ext = _extension_for(content_type)
        path = f"restaurants/{restaurant_id}/logo/{uuid.uuid4().hex}{ext}"
        self._db.storage.from_(ASSET_BUCKET).upload(
            path,
            data,
            {"content-type": content_type},
        )
        public_url = self._db.storage.from_(ASSET_BUCKET).get_public_url(path)
        self._db.table("restaurants").update({"logo_url": public_url}).eq("id", restaurant_id).execute()
        return public_url

    # -- ownership guards (explicit, server-derived) ------------------------

    def _require_restaurant(self, user_id: str, restaurant_id: str) -> dict:
        rows = (
            self._db.table("restaurants")
            .select("*")
            .eq("id", restaurant_id)
            .eq("owner_id", user_id)
            .execute()
        )
        if not rows.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
            )
        return rows.data[0]

    def _require_category(self, user_id: str, category_id: str) -> dict:
        rows = (
            self._db.table("categories")
            .select("*, restaurants!inner(owner_id)")
            .eq("id", category_id)
            .execute()
        )
        for row in rows.data or []:
            if row.get("restaurants") and row["restaurants"].get("owner_id") == user_id:
                return row
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    def _require_menu_item(self, user_id: str, item_id: str) -> dict:
        rows = (
            self._db.table("menu_items")
            .select("*, restaurants!inner(owner_id)")
            .eq("id", item_id)
            .execute()
        )
        for row in rows.data or []:
            if row.get("restaurants") and row["restaurants"].get("owner_id") == user_id:
                return row
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found"
        )


def _extension_for(content_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get((content_type or "").lower(), ".img")
