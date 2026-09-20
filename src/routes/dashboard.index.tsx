import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api/dashboard";

export const Route = createFileRoute("/dashboard/")({
  component: DashboardIndex,
});

function DashboardIndex() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => dashboardApi.getSummary(),
  });

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }

  if (isError || !data) {
    return <p className="text-sm text-destructive">Couldn't load your dashboard.</p>;
  }

  if (!data.restaurant) {
    return (
      <div className="mx-auto max-w-md rounded-3xl border border-border bg-card p-8 text-center">
        <h1 className="font-display text-2xl">Welcome to Dinevo</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Create your restaurant to start building its menu.
        </p>
        <Link
          to="/dashboard/restaurant"
          className="mt-5 inline-flex rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground"
        >
          Set up restaurant
        </Link>
      </div>
    );
  }

  const stats = [
    { label: "Total Dishes", value: data.menuItemCount },
    { label: "Available Dishes", value: data.availableDishCount },
    { label: "Categories", value: data.categoryCount },
    { label: "Inactive Categories", value: data.inactiveCategoryCount },
  ];

  return (
    <div>
      <h1 className="font-display text-3xl">{data.restaurant.name}</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {data.restaurant.description || "Your restaurant dashboard"}
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="rounded-3xl border border-border bg-card p-5">
            <p className="text-3xl font-semibold">{s.value}</p>
            <p className="mt-1 text-sm text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
