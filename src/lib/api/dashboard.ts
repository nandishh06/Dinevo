import { apiFetch, apiUpload } from "@/lib/api/client";
import type { Category, Dish } from "@/types";
import type { DashboardSummary, Restaurant } from "@/types/saas";

/**
 * Owner dashboard API. All calls go through the Dscape FastAPI backend, which
 * verifies the bearer token and scopes data to the authenticated owner.
 */

interface BackendRestaurant {
  id: string;
  owner_id: string;
  slug: string;
  name: string;
  logo_url: string | null;
  description: string | null;
  address: string | null;
  phone: string | null;
  created_at: string;
  updated_at: string;
}

interface BackendDashboardSummary {
  restaurant: BackendRestaurant | null;
  category_count: number;
  menu_item_count: number;
  image_count: number;
  available_dish_count: number;
  inactive_category_count: number;
}

interface BackendCategory {
  id: string;
  restaurant_id: string;
  name: string;
  sort_order: number;
  is_active: boolean;
}

interface BackendMenuItem {
  id: string;
  restaurant_id: string;
  category_id: string | null;
  name: string;
  description: string | null;
  price: number;
  image_url: string | null;
  is_available: boolean;
  is_featured: boolean;
  model_url: string | null;
  model_status: string | null;
  dietary: "VEG" | "NON_VEG" | "EGG" | null;
  ingredients: string[] | null;
  spice_level: 0 | 1 | 2 | 3 | null;
  calories: number | null;
  tags: string[] | null;
}

function toRestaurant(r: BackendRestaurant): Restaurant {
  return {
    id: r.id,
    ownerId: r.owner_id,
    slug: r.slug,
    name: r.name,
    logoUrl: r.logo_url,
    description: r.description,
    address: r.address,
    phone: r.phone,
    createdAt: r.created_at,
    updatedAt: r.updated_at,
  };
}

function toCategory(c: BackendCategory): Category {
  return {
    id: c.id,
    name: c.name,
    sortOrder: c.sort_order,
    isActive: c.is_active,
  };
}

function toDashboardSummary(s: BackendDashboardSummary): DashboardSummary {
  return {
    restaurant: s.restaurant ? toRestaurant(s.restaurant) : null,
    categoryCount: s.category_count,
    menuItemCount: s.menu_item_count,
    imageCount: s.image_count,
    availableDishCount: s.available_dish_count,
    inactiveCategoryCount: s.inactive_category_count,
  };
}

function toDish(m: BackendMenuItem): Dish {
  const dish: Dish = {
    id: m.id,
    name: m.name,
    description: m.description ?? "",
    price: m.price,
    categoryId: m.category_id ?? "",
    imageUrl: m.image_url ?? "",
    isAvailable: m.is_available,
    isFeatured: m.is_featured,
    modelStatus: m.model_status ?? null,
  };
  if (m.model_url) dish.modelUrl = m.model_url;
  if (m.dietary) dish.dietary = m.dietary;
  if (m.tags) dish.tags = m.tags;
  if (m.ingredients) dish.ingredients = m.ingredients;
  if (m.spice_level != null) dish.spiceLevel = m.spice_level;
  if (m.calories != null) dish.calories = m.calories;
  return dish;
}

export const dashboardApi = {
  // summary
  getSummary: () =>
    apiFetch<BackendDashboardSummary>("/dashboard", { auth: true }).then(
      toDashboardSummary,
    ),

  // restaurant
  getRestaurant: () =>
    apiFetch<BackendRestaurant>("/dashboard/restaurant", { auth: true }).then(
      toRestaurant,
    ),
  createRestaurant: (name: string) =>
    apiFetch<BackendRestaurant>("/dashboard/restaurant", {
      method: "POST",
      body: { name },
      auth: true,
    }).then(toRestaurant),
  updateRestaurant: (fields: Partial<Restaurant>) =>
    apiFetch<BackendRestaurant>("/dashboard/restaurant", {
      method: "PATCH",
      body: fields,
      auth: true,
    }).then(toRestaurant),

  // categories
  getCategories: () =>
    apiFetch<BackendCategory[]>("/dashboard/categories", { auth: true }).then(
      (rows) => rows.map(toCategory),
    ),
  createCategory: (name: string, sortOrder = 0) =>
    apiFetch<BackendCategory>("/dashboard/categories", {
      method: "POST",
      body: { name, sort_order: sortOrder },
      auth: true,
    }).then(toCategory),
  updateCategory: (
    id: string,
    fields: { name?: string; sortOrder?: number; isActive?: boolean },
  ) =>
    apiFetch<BackendCategory>(`/dashboard/categories/${id}`, {
      method: "PATCH",
      body: fields,
      auth: true,
    }).then(toCategory),
  deleteCategory: (id: string) =>
    apiFetch<void>(`/dashboard/categories/${id}`, {
      method: "DELETE",
      auth: true,
    }),

  // menu items
  getMenuItems: () =>
    apiFetch<BackendMenuItem[]>("/dashboard/menu", { auth: true }).then(
      (rows) => rows.map(toDish),
    ),
  createMenuItem: (fields: Record<string, unknown>) =>
    apiFetch<BackendMenuItem>("/dashboard/menu", {
      method: "POST",
      body: fields,
      auth: true,
    }).then(toDish),
  updateMenuItem: (id: string, fields: Record<string, unknown>) =>
    apiFetch<BackendMenuItem>(`/dashboard/menu/${id}`, {
      method: "PATCH",
      body: fields,
      auth: true,
    }).then(toDish),
  deleteMenuItem: (id: string) =>
    apiFetch<void>(`/dashboard/menu/${id}`, { method: "DELETE", auth: true }),

  // image upload
  uploadMenuItemImage: (id: string, file: File) =>
    apiUpload<{ item_id: string; image_url: string }>(
      `/dashboard/menu/${id}/image`,
      file,
    ),
  uploadRestaurantLogo: (file: File) =>
    apiUpload<BackendRestaurant>(`/dashboard/restaurant/logo`, file).then(
      toRestaurant,
    ),

  // 3D generation
  generateMenuItem: (id: string) =>
    apiFetch<{ generation_id: string; menu_item_id: string; status: string }>(
      `/dashboard/menu/${id}/generate`,
      { method: "POST", auth: true },
    ),
  getMenuItemGeneration: (id: string) =>
    apiFetch<{
      id: string;
      menu_item_id: string;
      provider: string;
      provider_task_id: string | null;
      status: string;
      glb_url: string | null;
      usdz_url: string | null;
      error: string | null;
      created_at: string;
      updated_at: string;
    } | null>(`/dashboard/menu/${id}/generation`, { auth: true }),
  retryGeneration: (id: string) =>
    apiFetch<{ generation_id: string; menu_item_id: string; status: string }>(
      `/dashboard/menu/${id}/generation/retry`,
      { method: "POST", auth: true },
    ),
};
