import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Box, Flame, Sparkles } from "lucide-react";
import { AppHeader } from "@/components/layout/AppHeader";
import { DietaryMark } from "@/components/ui/dietary-mark";
import { DishImage } from "@/components/ui/dish-image";
import { SkeletonBlock, StateMessage } from "@/components/ui/state-message";
import { publicDishQuery } from "@/features/menu/queries";
import { formatPrice } from "@/lib/utils/format";

export const Route = createFileRoute("/t/$token/dish/$dishId")({
  head: () => ({
    meta: [
      { title: "Dish details — Dinevo Dine AR" },
      {
        name: "description",
        content:
          "Full-plate photography, ingredients and dietary details, plus a 3D and AR preview of the dish.",
      },
      { property: "og:title", content: "Dish details — Dinevo Dine AR" },
      {
        property: "og:description",
        content:
          "Full-plate photography, ingredients and dietary details, plus a 3D and AR preview of the dish.",
      },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: DishDetailPage,
});

function DishDetailPage() {
  const { token } = Route.useParams();
  return (
    <div className="min-h-screen pb-16">
      <AppHeader token={token} />
      <DishDetail />
    </div>
  );
}

function DishDetail() {
  const { dishId, token } = Route.useParams();
  const router = useRouter();
  const {
    data: dish,
    isLoading,
    isError,
  } = useQuery(publicDishQuery(token, dishId));

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 px-4 py-6 sm:px-6">
        <SkeletonBlock className="aspect-[4/3] w-full" />
        <SkeletonBlock className="h-8 w-2/3" />
        <SkeletonBlock className="h-24 w-full" />
      </div>
    );
  }

  if (isError || !dish) {
    return (
      <StateMessage
        title="This dish isn't on the menu"
        description="It may have been removed by the kitchen. Head back to browse what's available."
        action={
          <Link
            to="/t/$token"
            params={{ token }}
            className="mt-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground"
          >
            Back to menu
          </Link>
        }
      />
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-4 pt-4 pb-6 sm:px-6">
      <button
        type="button"
        onClick={() => router.history.back()}
        className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft aria-hidden className="size-4" /> Back
      </button>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* The photograph is the primary experience — 3D is opt-in. */}
        <div className="relative overflow-hidden rounded-3xl shadow-lift">
          <DishImage
            src={dish.imageUrl}
            alt={dish.name}
            priority
            className="aspect-[4/3] w-full"
          />
          {!dish.isAvailable ? (
            <span className="absolute inset-0 flex items-center justify-center bg-surface-strong/65 font-semibold text-background">
              Currently unavailable
            </span>
          ) : null}
        </div>

        <div>
          <div className="flex items-center gap-2">
            <DietaryMark dietary={dish.dietary} />
            <span className="eyebrow">
              {dish.tags?.[0] ?? "From the kitchen"}
            </span>
          </div>
          <h1 className="mt-2 font-display text-3xl sm:text-4xl">
            {dish.name}
          </h1>
          <p className="mt-2 font-display text-2xl font-semibold">
            {formatPrice(dish.price)}
          </p>
          <p className="mt-4 leading-relaxed text-muted-foreground">
            {dish.description}
          </p>

          <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
            {dish.calories ? (
              <div className="rounded-2xl bg-surface p-3">
                <dt className="text-xs text-muted-foreground">Energy</dt>
                <dd className="font-semibold">{dish.calories} kcal</dd>
              </div>
            ) : null}
            {typeof dish.spiceLevel === "number" ? (
              <div className="rounded-2xl bg-surface p-3">
                <dt className="text-xs text-muted-foreground">Spice</dt>
                <dd className="flex items-center gap-1 font-semibold">
                  {dish.spiceLevel === 0
                    ? "Not spicy"
                    : Array.from({ length: dish.spiceLevel }).map((_, i) => (
                        <Flame
                          key={i}
                          aria-hidden
                          className="size-4 text-nonveg"
                        />
                      ))}
                  <span className="sr-only">
                    Spice level {dish.spiceLevel} of 3
                  </span>
                </dd>
              </div>
            ) : null}
          </dl>

          {dish.ingredients?.length ? (
            <section className="mt-5">
              <h2 className="eyebrow">Ingredients</h2>
              <ul className="mt-2 flex flex-wrap gap-2">
                {dish.ingredients.map((item) => (
                  <li
                    key={item}
                    className="rounded-full bg-secondary px-3 py-1 text-sm text-secondary-foreground"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Link
              to="/t/$token/ar/$dishId"
              params={{ token, dishId: dish.id }}
              search={{ mode: "ar" as const }}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-full bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground shadow-lift transition-transform duration-150 active:scale-[0.98]"
            >
              <Sparkles aria-hidden className="size-4" />
              View in AR
            </Link>
            {dish.modelUrl ? (
              <Link
                to="/t/$token/ar/$dishId"
                params={{ token, dishId: dish.id }}
                search={{ mode: "3d" as const }}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-border bg-card px-6 py-3.5 text-sm font-semibold hover:bg-secondary"
              >
                <Box aria-hidden className="size-4" /> View 3D
              </Link>
            ) : null}
          </div>
        </div>
      </div>
    </main>
  );
}
