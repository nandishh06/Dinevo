export interface Category {
  id: string;
  name: string;
  sortOrder: number;
  isActive?: boolean;
}

export type DietaryType = "VEG" | "NON_VEG" | "EGG";

export interface Dish {
  id: string;
  name: string;
  description: string;
  /** Menu display price in minor-unit-free rupees. Never authoritative. */
  price: number;
  categoryId: string;
  imageUrl: string;
  /** Optional 3D asset. Loaded lazily, only on explicit user intent. */
  modelUrl?: string;
  /** Generation state: null | GENERATING | READY | FAILED. */
  modelStatus?: string | null;
  isAvailable: boolean;
  isFeatured: boolean;
  dietary?: DietaryType;
  tags?: string[];
  ingredients?: string[];
  spiceLevel?: 0 | 1 | 2 | 3;
  /** Kilocalories, when the kitchen has published it. */
  calories?: number;
}

/** Filter contract — additive by design so future filters need no rewrite. */
export interface MenuFilters {
  categoryId?: string;
  query?: string;
  dietary?: DietaryType;
  tag?: string;
}
