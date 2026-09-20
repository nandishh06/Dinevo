import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { UtensilsCrossed } from "lucide-react";
import { publicMenuQuery } from "@/features/menu/queries";

/**
 * Compact customer-menu header. Resolves the restaurant name from the
 * real public menu for the restaurant slug in the URL.
 */
export function AppHeader({ token }: { token: string }) {
  const { data: menu } = useQuery(publicMenuQuery(token));
  const restaurantName = menu?.restaurant.name;
  const restaurantLogo = menu?.restaurant.logoUrl;

  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3 sm:px-6">
        <Link
          to="/t/$token"
          params={{ token }}
          className="flex min-w-0 items-center gap-3"
          aria-label="Back to menu"
        >
          {restaurantLogo ? (
            <img
              src={restaurantLogo}
              alt=""
              className="size-10 shrink-0 rounded-full object-cover"
            />
          ) : (
            <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-strong text-background">
              <UtensilsCrossed aria-hidden className="size-5" />
            </span>
          )}
          <span className="min-w-0">
            <span className="block truncate font-display text-base leading-tight font-semibold">
              {restaurantName ?? "Dinevo"}
            </span>
            <span className="block truncate text-xs text-muted-foreground">
              {restaurantName ? "Menu" : "Opening menu…"}
            </span>
          </span>
        </Link>
      </div>
    </header>
  );
}
