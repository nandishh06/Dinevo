import { Navigate } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { useAuth } from "@/features/auth/AuthProvider";

/**
 * Client-side auth guard for the owner dashboard.
 *
 * During SSR/hydration `loading` is true and we render a minimal placeholder;
 * once the browser resolves the Supabase session we either render the children
 * or redirect to /login. Real authorization is enforced by the backend (JWT
 * verification + owner scoping); this guard is a UX convenience only.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
