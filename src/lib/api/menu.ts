import { apiFetch, ApiError } from "@/lib/api/client";
import type { Category, Dish } from "@/types";
import type { Restaurant } from "@/types/saas";

/**
 * Customer-facing public menu. Reads real Supabase data through the Dscape
 * backend (no auth required — the menu is public to guests).
 */

interface PublicMenuResponse {
  restaurant: {
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
  };
  categories: {
    id: string;
    restaurant_id: string;
    name: string;
    sort_order: number;
  }[];
  menu_items: {
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
  }[];
}

export interface PublicMenu {
  restaurant: Restaurant;
  categories: Category[];
  dishes: Dish[];
}

export async function getPublicMenu(slug: string): Promise<PublicMenu> {
  const data = await apiFetch<PublicMenuResponse>(`/menu/${slug}`);
  return {
    restaurant: {
      id: data.restaurant.id,
      ownerId: data.restaurant.owner_id,
      slug: data.restaurant.slug,
      name: data.restaurant.name,
      logoUrl: data.restaurant.logo_url,
      description: data.restaurant.description,
      address: data.restaurant.address,
      phone: data.restaurant.phone,
      createdAt: data.restaurant.created_at,
      updatedAt: data.restaurant.updated_at,
    },
    categories: data.categories.map((c) => ({
      id: c.id,
      name: c.name,
      sortOrder: c.sort_order,
    })),
    dishes: data.menu_items.map((m) => {
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
    }),
  };
}

export async function getPublicDish(
  slug: string,
  dishId: string,
): Promise<Dish> {
  const menu = await getPublicMenu(slug);
  const dish = menu.dishes.find((d) => d.id === dishId);
  if (!dish) {
    throw new ApiError(404, "Dish not found");
  }
  return dish;
}
