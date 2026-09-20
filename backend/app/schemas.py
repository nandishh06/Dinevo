"""Pydantic response/request schemas.

These are the API boundary types. ORM objects are never returned directly, so
DB internals (and any future secrets) stay out of HTTP responses.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


# ---------------------------------------------------------------------------
# SaaS dashboard / menu schemas
# ---------------------------------------------------------------------------

class RestaurantCreate(BaseModel):
    name: str


class RestaurantUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    address: str | None = None
    phone: str | None = None
    logo_url: str | None = None


class RestaurantOut(BaseModel):
    id: str
    owner_id: str
    slug: str
    name: str
    logo_url: str | None = None
    description: str | None = None
    address: str | None = None
    phone: str | None = None
    created_at: datetime
    updated_at: datetime


class CategoryCreate(BaseModel):
    name: str
    sort_order: int = 0
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    id: str
    restaurant_id: str
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MenuItemCreate(BaseModel):
    category_id: str | None = None
    name: str
    description: str | None = None
    price: int = 0
    is_available: bool = True
    dietary: str | None = None
    ingredients: list[str] | None = None
    spice_level: int | None = None
    calories: int | None = None
    tags: list[str] | None = None
    sort_order: int = 0


class MenuItemUpdate(BaseModel):
    category_id: str | None = None
    name: str | None = None
    description: str | None = None
    price: int | None = None
    is_available: bool | None = None
    dietary: str | None = None
    ingredients: list[str] | None = None
    spice_level: int | None = None
    calories: int | None = None
    tags: list[str] | None = None
    sort_order: int | None = None


class MenuItemOut(BaseModel):
    id: str
    restaurant_id: str
    category_id: str | None = None
    name: str
    description: str | None = None
    price: int
    image_url: str | None = None
    is_available: bool
    is_featured: bool = False
    model_url: str | None = None
    model_status: str | None = None
    dietary: str | None = None
    ingredients: list[str] | None = None
    spice_level: int | None = None
    calories: int | None = None
    tags: list[str] | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ImageUploadOut(BaseModel):
    item_id: str
    image_url: str


class DashboardSummary(BaseModel):
    restaurant: RestaurantOut | None
    category_count: int
    menu_item_count: int
    image_count: int
    available_dish_count: int
    inactive_category_count: int


class PublicMenu(BaseModel):
    restaurant: RestaurantOut
    categories: list[CategoryOut]
    menu_items: list[MenuItemOut]


# ---------------------------------------------------------------------------
# SaaS 3D generation (Supabase) schemas
# ---------------------------------------------------------------------------

class GenerationJobCreate(BaseModel):
    generation_id: str
    menu_item_id: str
    status: str


class GenerationJobOut(BaseModel):
    id: str
    menu_item_id: str
    provider: str
    provider_task_id: str | None = None
    status: str
    glb_url: str | None = None
    usdz_url: str | None = None
    preview_urls: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
