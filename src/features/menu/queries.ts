import { queryOptions } from "@tanstack/react-query";
import { getPublicDish, getPublicMenu } from "@/lib/api/menu";

/**
 * Real Supabase-backed menu for a restaurant, keyed by its slug (the token in
 * the current customer URL). Returns null when the restaurant doesn't exist or
 * the backend isn't reachable, so the route can render a not-found state.
 */
export const publicMenuQuery = (slug: string) =>
  queryOptions({
    queryKey: ["public-menu", slug],
    queryFn: () => getPublicMenu(slug).catch(() => null),
    staleTime: 5_000,
    retry: false,
  });

export const publicDishQuery = (slug: string, dishId: string) =>
  queryOptions({
    queryKey: ["public-dish", slug, dishId],
    queryFn: () => getPublicDish(slug, dishId),
    staleTime: 60_000,
    retry: false,
  });
