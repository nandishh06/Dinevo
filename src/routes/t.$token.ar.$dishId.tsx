import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { AppHeader } from "@/components/layout/AppHeader";
import { DishARViewer } from "@/components/ar/DishARViewer";
import { DishImage } from "@/components/ui/dish-image";
import { SkeletonBlock, StateMessage } from "@/components/ui/state-message";
import { publicDishQuery } from "@/features/menu/queries";

type ArMode = "3d" | "ar";

export const Route = createFileRoute("/t/$token/ar/$dishId")({
  validateSearch: (search: Record<string, unknown>): { mode: ArMode } => ({
    mode: search["mode"] === "ar" ? "ar" : "3d",
  }),
  head: () => ({
    meta: [
      { title: "3D & AR preview — Dinevo Dine AR" },
      {
        name: "description",
        content:
          "Rotate the plated dish in 3D, or place it on your own table with augmented reality.",
      },
      { property: "og:title", content: "3D & AR preview — Dinevo Dine AR" },
      {
        property: "og:description",
        content:
          "Rotate the plated dish in 3D, or place it on your own table with augmented reality.",
      },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ArPage,
});

function ArPage() {
  const { dishId, token } = Route.useParams();
  const { mode } = Route.useSearch();
  const router = useRouter();
  const {
    data: dish,
    isLoading,
    isError,
  } = useQuery(publicDishQuery(token, dishId));

  return (
    <div className="min-h-screen">
      <AppHeader token={token} />
      <main className="mx-auto max-w-2xl px-4 py-6 sm:px-6">
        <button
          type="button"
          onClick={() => router.history.back()}
          className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft aria-hidden className="size-4" /> Back
        </button>

        {isLoading ? (
          <SkeletonBlock className="aspect-square w-full" />
        ) : isError || !dish ? (
          <StateMessage
            title="Dish unavailable"
            description="We couldn't load this dish for 3D preview."
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
        ) : (
          <>
            <h1 className="font-display text-2xl">
              {dish.modelUrl
                ? mode === "ar"
                  ? `${dish.name} — in your space`
                  : `${dish.name} — 3D preview`
                : `${dish.name} — in your space`}
            </h1>
            <p className="mt-1 mb-4 text-sm text-muted-foreground">
              {dish.modelUrl
                ? mode === "ar"
                  ? "Place the dish on your table in AR — move, resize and walk around it."
                  : "The 3D model loads only on this screen, so browsing the menu stays fast."
                : "Point your camera at the table and place the dish photo wherever it looks right."}
            </p>

            <DishARViewer
              modelUrl={dish.modelUrl}
              dishName={dish.name}
              imageUrl={dish.imageUrl}
              posterUrl={dish.imageUrl}
              mode={mode}
            />

            <section className="mt-6">
              <h2 className="eyebrow">The actual plating</h2>
              <div className="mt-2 overflow-hidden rounded-3xl shadow-card">
                <DishImage
                  src={dish.imageUrl}
                  alt={dish.name}
                  className="aspect-[4/3] w-full"
                />
              </div>
            </section>

            <Link
              to="/t/$token/dish/$dishId"
              params={{ token, dishId: dish.id }}
              className="mt-5 inline-flex rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground"
            >
              Back to dish details
            </Link>
          </>
        )}
      </main>
    </div>
  );
}
