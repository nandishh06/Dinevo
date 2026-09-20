import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { SearchX } from "lucide-react";
import { AppHeader } from "@/components/layout/AppHeader";
import { CategoryNav } from "@/components/menu/CategoryNav";
import { FeaturedRail } from "@/components/menu/FeaturedRail";
import { MenuSearch } from "@/components/menu/MenuSearch";
import { DishCard } from "@/components/dish/DishCard";
import { StateMessage, SkeletonBlock } from "@/components/ui/state-message";
import { publicMenuQuery } from "@/features/menu/queries";

const TITLE = "Restaurant menu — Dinevo Dine AR";
const DESCRIPTION =
  "Browse the full restaurant menu with dish photography and 3D / AR dish previews.";

export const Route = createFileRoute("/t/$token/")({
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: MenuPage,
});

function MenuPage() {
  const { token } = Route.useParams();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!token) return;
    const refetch = () => {
      void queryClient.invalidateQueries({ queryKey: ["public-menu", token] });
    };
    const interval = window.setInterval(refetch, 5000);
    const onVisible = () => {
      if (document.visibilityState === "visible") refetch();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [queryClient, token]);

  return (
    <div className="min-h-screen pb-16">
      <AppHeader token={token} />
      <MenuContent />
    </div>
  );
}

function MenuContent() {
  const { token } = Route.useParams();
  const [categoryId, setCategoryId] = useState("all");
  const [query, setQuery] = useState("");

  const realMenu = useQuery(publicMenuQuery(token));

  const activeCategories = realMenu.data?.categories ?? [];
  const activeDishes = realMenu.data?.dishes ?? [];
  const restaurantName = realMenu.data?.restaurant.name;

  const featured = useMemo(
    () => activeDishes.filter((d) => d.isFeatured),
    [activeDishes],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return activeDishes.filter((dish) => {
      if (categoryId !== "all" && dish.categoryId !== categoryId) return false;
      if (!q) return true;
      return `${dish.name} ${dish.description} ${(dish.tags ?? []).join(" ")}`
        .toLowerCase()
        .includes(q);
    });
  }, [activeDishes, categoryId, query]);

  if (realMenu.isLoading) {
    return (
      <div className="mx-auto max-w-6xl space-y-4 px-4 py-10 sm:px-6">
        <SkeletonBlock className="h-8 w-48" />
        <SkeletonBlock className="h-56 w-full" />
        <SkeletonBlock className="h-40 w-full" />
      </div>
    );
  }

  if (!realMenu.data) {
    return (
      <StateMessage
        title="Restaurant not found"
        description="This menu link doesn't match an active restaurant. Check the QR code and try again."
      />
    );
  }

  return (
    <main>
      <section className="px-4 pt-8 pb-4 sm:px-6">
        <p className="eyebrow">{restaurantName}</p>
        <h1 className="mt-3 font-display text-4xl leading-[1.05] sm:text-5xl">
          Good food.
          <br />
          Better experiences.
        </h1>
        <p className="mt-3 max-w-prose text-sm leading-relaxed text-muted-foreground">
          Welcome to {restaurantName}. Explore the menu and see selected dishes
          in your space before you decide.
        </p>
        <div className="mt-6 max-w-xl">
          <MenuSearch value={query} onChange={setQuery} />
        </div>
      </section>

      {query.trim() === "" && categoryId === "all" ? (
        <FeaturedRail dishes={featured} token={token} />
      ) : null}

      <section
        aria-labelledby="full-menu-heading"
        className="px-4 pt-6 sm:px-6"
      >
        <h2 id="full-menu-heading" className="eyebrow">
          Full menu
        </h2>
      </section>

      <CategoryNav
        categories={activeCategories}
        activeId={categoryId}
        onSelect={setCategoryId}
      />

      <section aria-label="Dishes" className="px-4 pb-14 sm:px-6">
        {visible.length === 0 ? (
          <StateMessage
            icon={<SearchX aria-hidden className="size-8" />}
            title="Nothing matches that search"
            description="Try a different dish, or clear the search to see the full menu."
          />
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {visible.map((dish) => (
              <li key={dish.id}>
                <DishCard dish={dish} token={token} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
