/** SaaS domain types — camelCase mirror of the Supabase schema. */

export interface Restaurant {
  id: string;
  ownerId: string;
  slug: string;
  name: string;
  logoUrl: string | null;
  description: string | null;
  address: string | null;
  phone: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DashboardSummary {
  restaurant: Restaurant | null;
  categoryCount: number;
  menuItemCount: number;
  imageCount: number;
  availableDishCount: number;
  inactiveCategoryCount: number;
}
