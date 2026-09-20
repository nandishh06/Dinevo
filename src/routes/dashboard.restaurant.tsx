import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { ImagePlus } from "lucide-react";
import { MenuQrCode } from "@/components/qr/MenuQrCode";
import { ApiError } from "@/lib/api/client";
import { dashboardApi } from "@/lib/api/dashboard";

export const Route = createFileRoute("/dashboard/restaurant")({
  component: RestaurantPage,
});

function RestaurantPage() {
  const queryClient = useQueryClient();
  const {
    data: restaurant,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["dashboard-restaurant"],
    queryFn: () =>
      dashboardApi.getRestaurant().catch((e) => {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }),
  });

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Sync form fields whenever the restaurant loads/changes (keeps inputs
  // controlled and clearable).
  useEffect(() => {
    if (restaurant) {
      setName(restaurant.name);
      setDescription(restaurant.description ?? "");
      setAddress(restaurant.address ?? "");
      setPhone(restaurant.phone ?? "");
    }
  }, [restaurant]);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard-restaurant"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  };

  const createMutation = useMutation({
    mutationFn: (n: string) => dashboardApi.createRestaurant(n),
    onSuccess: () => {
      invalidate();
      setMessage("Restaurant created.");
    },
    onError: (e: Error) => setError(e.message),
  });

  const updateMutation = useMutation({
    mutationFn: (fields: Parameters<typeof dashboardApi.updateRestaurant>[0]) =>
      dashboardApi.updateRestaurant(fields),
    onSuccess: () => {
      invalidate();
      setMessage("Restaurant updated.");
    },
    onError: (e: Error) => setError(e.message),
  });

  const logoMutation = useMutation({
    mutationFn: (file: File) => dashboardApi.uploadRestaurantLogo(file),
    onSuccess: () => {
      invalidate();
      setMessage("Logo updated.");
    },
    onError: (e: Error) => setError(e.message),
  });

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }

  if (isError) {
    return (
      <p className="text-sm text-destructive">Couldn't load your restaurant.</p>
    );
  }

  if (!restaurant) {
    return (
      <div className="mx-auto max-w-md">
        <h1 className="font-display text-3xl">Restaurant</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Create your restaurant profile to get started.
        </p>
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            setError(null);
            if (name.trim()) createMutation.mutate(name.trim());
          }}
          className="mt-6 space-y-4"
        >
          <div>
            <label htmlFor="rname" className="text-sm font-semibold">
              Restaurant name
            </label>
            <input
              id="rname"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="mt-1 w-full rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus-visible:border-ring"
            />
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
          >
            {createMutation.isPending ? "Creating…" : "Create restaurant"}
          </button>
        </form>
      </div>
    );
  }

  function onUpdate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    updateMutation.mutate({ name: name.trim(), description, address, phone });
  }

  const customerUrl =
    typeof window === "undefined"
      ? `/t/${restaurant.slug}`
      : `${window.location.origin}/t/${restaurant.slug}`;

  return (
    <div className="max-w-2xl">
      <h1 className="font-display text-3xl">Restaurant</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Manage your restaurant profile and contact details.
      </p>

      <div className="mt-6 flex items-center gap-4">
        {restaurant.logoUrl ? (
          <img
            src={restaurant.logoUrl}
            alt="Restaurant logo"
            className="size-24 rounded-2xl object-cover"
          />
        ) : (
          <span className="flex size-24 flex-col items-center justify-center gap-1 rounded-2xl bg-secondary text-xs text-muted-foreground">
            <ImagePlus aria-hidden className="size-6" />
            No logo
          </span>
        )}
        <label className="inline-flex cursor-pointer items-center rounded-full border border-border bg-card px-5 py-2.5 text-sm font-semibold hover:bg-secondary">
          {logoMutation.isPending ? "Uploading…" : "Upload logo"}
          <input
            type="file"
            accept="image/*"
            className="hidden"
            disabled={logoMutation.isPending}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) logoMutation.mutate(file);
            }}
          />
        </label>
      </div>

      <form onSubmit={onUpdate} className="mt-6 space-y-4">
        <div>
          <label htmlFor="rname" className="text-sm font-semibold">
            Name
          </label>
          <input
            id="rname"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="mt-1 w-full rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus-visible:border-ring"
          />
        </div>
        <div>
          <label htmlFor="rdesc" className="text-sm font-semibold">
            Description
          </label>
          <textarea
            id="rdesc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="mt-1 w-full rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus-visible:border-ring"
          />
        </div>
        <div>
          <label htmlFor="raddr" className="text-sm font-semibold">
            Address
          </label>
          <input
            id="raddr"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="mt-1 w-full rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus-visible:border-ring"
          />
        </div>
        <div>
          <label htmlFor="rphone" className="text-sm font-semibold">
            Phone
          </label>
          <input
            id="rphone"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="mt-1 w-full rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus-visible:border-ring"
          />
        </div>

        {message ? <p className="text-sm text-veg">{message}</p> : null}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <button
          type="submit"
          disabled={updateMutation.isPending}
          className="rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
        >
          {updateMutation.isPending ? "Saving…" : "Save changes"}
        </button>
      </form>

      <section className="mt-8 rounded-3xl border border-border bg-card p-6">
        <h2 className="font-display text-xl">Customer Menu QR</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Print or save this code. Guests who scan it open your live menu.
        </p>

        <div className="mt-4 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <MenuQrCode
            path={`/t/${restaurant.slug}`}
            downloadName={`${restaurant.slug}-menu-qr.png`}
          />
          <div className="w-full space-y-3">
            <div>
              <p className="text-xs font-semibold text-muted-foreground">
                Customer URL
              </p>
              <div className="mt-1 flex items-center gap-2">
                <input
                  readOnly
                  value={customerUrl}
                  className="w-full min-w-0 rounded-lg border border-border bg-background px-3 py-2 text-xs text-muted-foreground outline-none"
                />
                <button
                  type="button"
                  onClick={() =>
                    void navigator.clipboard.writeText(customerUrl)
                  }
                  className="shrink-0 rounded-full border border-border px-3 py-2 text-xs font-semibold hover:bg-secondary"
                >
                  Copy
                </button>
              </div>
            </div>

            <Link
              to="/t/$token"
              params={{ token: restaurant.slug }}
              className="inline-flex rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
            >
              Open customer menu
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
