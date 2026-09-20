import { Link } from "@tanstack/react-router";
import { Box } from "lucide-react";
import { DishImage } from "@/components/ui/dish-image";
import { formatPrice } from "@/lib/utils/format";
import type { Dish } from "@/types";

/** Data-driven: every card comes from `isFeatured` dishes, never hard-coded JSX. */
export function FeaturedRail({ dishes, token }: { dishes: Dish[]; token: string }) {
  if (dishes.length === 0) return null;
  return (
    <section aria-labelledby="featured-heading" className="pt-2">
      <div className="flex items-baseline justify-between px-4 sm:px-6">
        <h2 id="featured-heading" className="eyebrow">
          Featured today
        </h2>
        <span className="text-xs text-muted-foreground">{dishes.length} picks</span>
      </div>
      <ul className="no-scrollbar mt-3 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-2 sm:px-6">
        {dishes.map((dish, index) => (
          <li key={dish.id} className="w-[82%] max-w-sm shrink-0 snap-start sm:w-[420px]">
            <Link
              to="/t/$token/dish/$dishId"
              params={{ token, dishId: dish.id }}
              className="group relative block aspect-[5/6] overflow-hidden rounded-3xl shadow-lift sm:aspect-[16/10]"
            >
              <DishImage
                src={dish.imageUrl}
                alt={dish.name}
                priority={index === 0}
                className="size-full transition-transform duration-700 group-hover:scale-105"
              />
              <div
                aria-hidden
                className="absolute inset-0 bg-gradient-to-t from-surface-strong/90 via-surface-strong/25 to-transparent"
              />
              {dish.modelUrl ? (
                <span className="absolute top-4 left-4 inline-flex items-center gap-1 rounded-full bg-card/90 px-3 py-1 text-[11px] font-bold shadow-card">
                  <Box aria-hidden className="size-3" /> 3D / AR
                </span>
              ) : null}
              <div className="absolute inset-x-0 bottom-0 p-5 text-background">
                <p className="font-display text-2xl leading-tight font-semibold">
                  {dish.name}
                </p>
                <p className="mt-1 line-clamp-1 text-sm opacity-80">{dish.description}</p>
                <div className="mt-3 flex items-center gap-3">
                  <span className="text-lg font-semibold">{formatPrice(dish.price)}</span>
                  <span className="rounded-full bg-accent px-4 py-1.5 text-sm font-semibold text-accent-foreground">
                    View dish
                  </span>
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
