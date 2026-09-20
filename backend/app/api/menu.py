"""Public customer menu API.

Serves one restaurant's menu (restaurant + categories + items) by slug. This is
the trusted server-side reader: it uses the service-role client (bypassing RLS)
because the customer-facing menu must be publicly readable without auth, while
the underlying tables remain owner-only under RLS.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import CategoryOut, MenuItemOut, PublicMenu, RestaurantOut
from app.supabase import SupabaseNotConfigured, get_supabase

router = APIRouter(prefix="/menu", tags=["menu"])


def _public_supabase():
    try:
        return get_supabase()
    except SupabaseNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured on the server",
        ) from exc


@router.get("/{slug}", response_model=PublicMenu)
def get_public_menu(slug: str, supabase=Depends(_public_supabase)) -> PublicMenu:
    restaurants = (
        supabase.table("restaurants")
        .select("*")
        .eq("slug", slug)
        .execute()
    )
    if not restaurants.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found"
        )
    restaurant = restaurants.data[0]

    categories = (
        supabase.table("categories")
        .select("*")
        .eq("restaurant_id", restaurant["id"])
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    ).data or []

    items = (
        supabase.table("menu_items")
        .select("*")
        .eq("restaurant_id", restaurant["id"])
        .eq("is_available", True)
        .order("sort_order")
        .execute()
    ).data or []

    return PublicMenu(
        restaurant=RestaurantOut(**restaurant),
        categories=[CategoryOut(**c) for c in categories],
        menu_items=[MenuItemOut(**i) for i in items],
    )
