import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Camera, Sparkles } from "lucide-react";
import { CameraArView } from "@/components/ar/CameraArView";
import { DishImage } from "@/components/ui/dish-image";
import { dashboardApi } from "@/lib/api/dashboard";
import type { Dish } from "@/types";

export const Route = createFileRoute("/dashboard/ar")({
  component: ArPage,
});

function ArPage() {
  const [activeDish, setActiveDish] = useState<Dish | null>(null);

  const categoriesQuery = useQuery({
    queryKey: ["dashboard-categories"],
    queryFn: () => dashboardApi.getCategories(),
  });
  const itemsQuery = useQuery({
    queryKey: ["dashboard-menu-items"],
    queryFn: () => dashboardApi.getMenuItems(),
  });

  const categories = categoriesQuery.data ?? [];
  const items = itemsQuery.data ?? [];

  const categoryNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of categories) map.set(c.id, c.name);
    return map;
  }, [categories]);

  const dishesWithImages = items.filter((dish) => dish.imageUrl);

  return (
    <div className="max-w-6xl">
      <h1 className="font-display text-3xl">AR</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Preview your dishes in AR using the photos already on your menu.
      </p>

      <section className="mt-6">
        <h2 className="eyebrow">2D AR</h2>
        {dishesWithImages.length === 0 ? (
          <div className="mt-4 rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            No dishes with photos yet. Add a dish photo from the Menu page.
          </div>
        ) : (
          <ul className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {dishesWithImages.map((dish) => (
              <li
                key={dish.id}
                className="overflow-hidden rounded-2xl border border-border bg-card"
              >
                <DishImage
                  src={dish.imageUrl}
                  alt={dish.name}
                  className="aspect-[4/3] w-full"
                />
                <div className="p-4">
                  <h3 className="text-base font-semibold">{dish.name}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {dish.categoryId
                      ? (categoryNameById.get(dish.categoryId) ??
                        "Uncategorized")
                      : "Uncategorized"}
                  </p>
                  <button
                    type="button"
                    onClick={() => setActiveDish(dish)}
                    className="mt-3 inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
                  >
                    <Camera aria-hidden className="size-4" />
                    View in AR
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-8 rounded-3xl border border-border bg-card p-6">
        <h2 className="font-display text-xl">3D AR</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Subscribe for 3D AR and generate interactive 3D models from your dish
          photos.
        </p>
        <button
          type="button"
          disabled
          className="mt-4 inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
        >
          <Sparkles aria-hidden className="size-4" />
          Subscribe for 3D AR
        </button>
        <p className="mt-2 text-xs text-muted-foreground">
          3D generation will be available after subscription.
        </p>
      </section>

      {activeDish ? (
        <CameraArView
          dishName={activeDish.name}
          imageUrl={activeDish.imageUrl}
          onClose={() => setActiveDish(null)}
        />
      ) : null}
    </div>
  );
}
