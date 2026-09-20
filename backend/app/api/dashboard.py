"""Owner dashboard API — authenticated, tenant-isolated CRUD.

Every route depends on `get_authenticated_user_id`, which verifies the Supabase
Auth bearer token and returns the server-verified owner UUID. All mutations are
then scoped to that owner by DashboardService.

The service-role Supabase client used here bypasses RLS, so explicit owner
scoping is mandatory; the database RLS policies are the independent backstop
for direct client access.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status

from app.config import load_settings
from app.schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    DashboardSummary,
    GenerationJobCreate,
    GenerationJobOut,
    ImageUploadOut,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
    RestaurantCreate,
    RestaurantOut,
    RestaurantUpdate,
)
from app.services.dashboard_service import DashboardService
from app.services.saas_generation import SaasGenerationService
from app.supabase import (
    SupabaseNotConfigured,
    get_authenticated_user_id,
    get_supabase,
)
from app.workers import run_saas_generation_in_background

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def get_dashboard_service() -> DashboardService:
    try:
        return DashboardService(get_supabase())
    except SupabaseNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured on the server",
        ) from exc


def get_saas_generation_service() -> SaasGenerationService:
    try:
        return SaasGenerationService(get_supabase())
    except SupabaseNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured on the server",
        ) from exc


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

@router.get("", response_model=DashboardSummary)
def dashboard_summary(
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummary:
    restaurant = service.get_restaurant(user_id)
    if restaurant is None:
        return DashboardSummary(
            restaurant=None,
            category_count=0,
            menu_item_count=0,
            image_count=0,
            available_dish_count=0,
            inactive_category_count=0,
        )
    categories = service.list_categories(user_id, restaurant["id"])
    items = service.list_menu_items(user_id, restaurant["id"])
    image_count = sum(1 for i in items if i.get("image_url"))
    available_dish_count = sum(1 for i in items if i.get("is_available"))
    inactive_category_count = sum(1 for c in categories if not c.get("is_active"))
    return DashboardSummary(
        restaurant=restaurant,
        category_count=len(categories),
        menu_item_count=len(items),
        image_count=image_count,
        available_dish_count=available_dish_count,
        inactive_category_count=inactive_category_count,
    )


# ---------------------------------------------------------------------------
# restaurant
# ---------------------------------------------------------------------------

@router.get("/restaurant", response_model=RestaurantOut)
def get_restaurant(
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> RestaurantOut:
    restaurant = service.get_restaurant(user_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No restaurant yet")
    return RestaurantOut(**restaurant)


@router.post("/restaurant", response_model=RestaurantOut, status_code=status.HTTP_201_CREATED)
def create_restaurant(
    body: RestaurantCreate,
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> RestaurantOut:
    existing = service.get_restaurant(user_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Restaurant already exists"
        )
    return RestaurantOut(**service.create_restaurant(user_id, name=body.name))


@router.patch("/restaurant", response_model=RestaurantOut)
def update_restaurant(
    body: RestaurantUpdate,
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> RestaurantOut:
    restaurant = service.get_restaurant(user_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No restaurant yet")
    return RestaurantOut(**service.update_restaurant(user_id, restaurant["id"], body.model_dump()))


@router.post("/restaurant/logo", response_model=RestaurantOut)
async def upload_restaurant_logo(
    file: UploadFile,
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> RestaurantOut:
    restaurant = service.get_restaurant(user_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No restaurant yet")
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image content type: {content_type or 'missing'}",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image upload")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large (max {MAX_IMAGE_BYTES} bytes)",
        )
    service.upload_restaurant_logo(user_id, restaurant["id"], data=data, content_type=content_type)
    updated = service.get_restaurant(user_id)
    return RestaurantOut(**updated)


# ---------------------------------------------------------------------------
# categories
# ---------------------------------------------------------------------------

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[CategoryOut]:
    restaurant = service.get_restaurant(user_id)
    if restaurant is None:
        return []
    return [CategoryOut(**c) for c in service.list_categories(user_id, restaurant["id"])]


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    body: CategoryCreate,
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> CategoryOut:
    restaurant = service.get_restaurant(user_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No restaurant yet")
    return CategoryOut(
        **service.create_category(
            user_id,
            restaurant["id"],
            name=body.name,
            sort_order=body.sort_order,
            is_active=body.is_active,
        )
    )


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: str,
    body: CategoryUpdate,
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> CategoryOut:
    return CategoryOut(**service.update_category(user_id, category_id, **body.model_dump(exclude_none=True)))


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: str,
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> None:
    service.delete_category(user_id, category_id)


# ---------------------------------------------------------------------------
# menu items
# ---------------------------------------------------------------------------

@router.get("/menu", response_model=list[MenuItemOut])
def list_menu_items(
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[MenuItemOut]:
    restaurant = service.get_restaurant(user_id)
    if restaurant is None:
        return []
    return [MenuItemOut(**i) for i in service.list_menu_items(user_id, restaurant["id"])]


@router.post("/menu", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
def create_menu_item(
    body: MenuItemCreate,
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> MenuItemOut:
    restaurant = service.get_restaurant(user_id)
    if restaurant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No restaurant yet")
    return MenuItemOut(**service.create_menu_item(user_id, restaurant["id"], body.model_dump()))


@router.patch("/menu/{item_id}", response_model=MenuItemOut)
def update_menu_item(
    item_id: str,
    body: MenuItemUpdate,
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> MenuItemOut:
    return MenuItemOut(**service.update_menu_item(user_id, item_id, body.model_dump(exclude_none=True)))


@router.delete("/menu/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    item_id: str,
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> None:
    service.delete_menu_item(user_id, item_id)


@router.post("/menu/{item_id}/image", response_model=ImageUploadOut)
async def upload_menu_item_image(
    item_id: str,
    file: UploadFile,
    user_id: str = Depends(get_authenticated_user_id),
    service: DashboardService = Depends(get_dashboard_service),
) -> ImageUploadOut:
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image content type: {content_type or 'missing'}",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image upload")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large (max {MAX_IMAGE_BYTES} bytes)",
        )
    url = service.upload_menu_item_image(user_id, item_id, data=data, content_type=content_type)
    return ImageUploadOut(item_id=item_id, image_url=url)


# ---------------------------------------------------------------------------
# 3D generation
# ---------------------------------------------------------------------------

@router.post(
    "/menu/{item_id}/generate",
    response_model=GenerationJobCreate,
    status_code=status.HTTP_201_CREATED,
)
def generate_menu_item_3d(
    item_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_authenticated_user_id),
    service: SaasGenerationService = Depends(get_saas_generation_service),
) -> GenerationJobCreate:
    """Start a 3D generation for a dish (async). Returns the generation id."""
    provider_name = load_settings().image_to_3d_provider or "fal"
    generation = service.create_generation(user_id, item_id, provider_name=provider_name)
    background_tasks.add_task(run_saas_generation_in_background, generation["id"])
    return GenerationJobCreate(
        generation_id=generation["id"],
        menu_item_id=generation["menu_item_id"],
        status=generation["status"],
    )


@router.get("/menu/{item_id}/generation", response_model=GenerationJobOut | None)
def get_menu_item_generation(
    item_id: str,
    user_id: str = Depends(get_authenticated_user_id),
    service: SaasGenerationService = Depends(get_saas_generation_service),
) -> GenerationJobOut | None:
    generation = service.get_generation(user_id, item_id)
    if generation is None:
        return None
    return GenerationJobOut(**generation)


@router.post(
    "/menu/{item_id}/generation/retry",
    response_model=GenerationJobCreate,
    status_code=status.HTTP_201_CREATED,
)
def retry_menu_item_generation(
    item_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_authenticated_user_id),
    service: SaasGenerationService = Depends(get_saas_generation_service),
) -> GenerationJobCreate:
    """Retry a failed generation (creates a NEW generation record)."""
    provider_name = load_settings().image_to_3d_provider or "fal"
    generation = service.create_generation(user_id, item_id, provider_name=provider_name)
    background_tasks.add_task(run_saas_generation_in_background, generation["id"])
    return GenerationJobCreate(
        generation_id=generation["id"],
        menu_item_id=generation["menu_item_id"],
        status=generation["status"],
    )
