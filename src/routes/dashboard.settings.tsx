import { createFileRoute } from "@tanstack/react-router";
import { useAuth } from "@/features/auth/AuthProvider";

export const Route = createFileRoute("/dashboard/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const { user } = useAuth();
  return (
    <div>
      <h1 className="font-display text-3xl">Settings</h1>
      <p className="mt-1 text-sm text-muted-foreground">Account information.</p>
      <div className="mt-6 max-w-md rounded-2xl border border-border bg-card p-5">
        <p className="text-sm font-semibold">Email</p>
        <p className="mt-1 text-sm text-muted-foreground">{user?.email ?? "—"}</p>
      </div>
    </div>
  );
}
