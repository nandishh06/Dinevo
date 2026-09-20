import { Link } from "@tanstack/react-router";
import { ArrowRight, Box } from "lucide-react";
import { DietaryMark } from "@/components/ui/dietary-mark";
import { DishImage } from "@/components/ui/dish-image";
import { formatPrice } from "@/lib/utils/format";
import type { Dish } from "@/types";

/** Presentation only — Phase 1 has no ordering affordances. */
export function DishCard({ dish, token }: { dish: Dish; token: string }) {
  return (
    <article className="group surface-card flex h-full flex-col overflow-hidden transition-shadow duration-200 hover:shadow-lift">
      <Link
        to="/t/$token/dish/$dishId"
        params={{ token, dishId: dish.id }}
        className="relative block aspect-[4/3] overflow-hidden"
        aria-label={`View ${dish.name}`}
      >
        <DishImage
          src={dish.imageUrl}
          alt={dish.name}
          className="size-full transition-transform duration-500 group-hover:scale-105"
        />
        {!dish.isAvailable ? (
          <span className="absolute inset-0 flex items-center justify-center bg-surface-strong/65 text-sm font-semibold text-background">
            Currently unavailable
          </span>
        ) : null}
        {dish.modelUrl ? (
          <span className="absolute top-3 left-3 inline-flex items-center gap-1 rounded-full bg-card/90 px-2.5 py-1 text-[11px] font-bold text-foreground shadow-card">
            <Box aria-hidden className="size-3" /> 3D / AR
          </span>
        ) : null}
      </Link>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-start gap-2">
          <DietaryMark dietary={dish.dietary} className="mt-0.5" />
          <h3 className="text-base leading-snug font-semibold">{dish.name}</h3>
        </div>
        <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">
          {dish.description}
        </p>
        {dish.tags?.length ? (
          <ul className="flex flex-wrap gap-1.5">
            {dish.tags.slice(0, 2).map((tag) => (
              <li
                key={tag}
                className="rounded-full bg-secondary px-2 py-0.5 text-[11px] font-semibold text-secondary-foreground"
              >
                {tag}
              </li>
            ))}
          </ul>
        ) : null}

        <div className="mt-auto flex items-center justify-between pt-3">
          <span className="font-display text-lg font-semibold">
            {formatPrice(dish.price)}
          </span>
          <Link
            to="/t/$token/dish/$dishId"
            params={{ token, dishId: dish.id }}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-4 py-2 text-sm font-semibold transition-colors hover:bg-secondary"
          >
            View dish
            <ArrowRight aria-hidden className="size-4" />
          </Link>
        </div>
      </div>
    </article>
  );
}
