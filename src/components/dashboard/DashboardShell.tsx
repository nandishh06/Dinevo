import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { LogOut, UtensilsCrossed } from "lucide-react";
import { useAuth } from "@/features/auth/AuthProvider";

const NAV = [
  { to: "/dashboard", label: "Overview", end: true },
  { to: "/dashboard/restaurant", label: "Restaurant" },
  { to: "/dashboard/menu", label: "Menu" },
  { to: "/dashboard/ar", label: "AR / 3D" },
  { to: "/dashboard/settings", label: "Settings" },
];

function navClass(active: boolean): string {
  return `block rounded-lg px-3 py-2 text-sm font-semibold transition-colors whitespace-nowrap ${
    active
      ? "bg-surface-strong text-background"
      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
  }`;
}

/**
 * Owner dashboard shell. Fixed left sidebar on desktop (lg+); a top bar with
 * horizontal nav on tablet/mobile.
 */
export function DashboardShell() {
  const { signOut, user } = useAuth();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const isActive = (to: string, end?: boolean) =>
    end ? pathname === to : pathname.startsWith(to);

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-border bg-card lg:flex">
        <div className="flex items-center gap-2 border-b border-border px-5 py-4">
          <span className="flex size-9 items-center justify-center rounded-full bg-surface-strong text-background">
            <UtensilsCrossed aria-hidden className="size-5" />
          </span>
          <span className="font-display text-lg font-semibold">Dinevo</span>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV.map((item) => (
            <Link key={item.to} to={item.to} className={navClass(isActive(item.to, item.end))}>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="border-t border-border px-5 py-4">
          <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
          <button
            type="button"
            onClick={() => void signOut()}
            className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-muted-foreground hover:text-foreground"
          >
            <LogOut aria-hidden className="size-4" /> Logout
          </button>
        </div>
      </aside>

      {/* Mobile / tablet top bar */}
      <header className="sticky top-0 z-30 border-b border-border bg-card lg:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="flex size-8 items-center justify-center rounded-full bg-surface-strong text-background">
              <UtensilsCrossed aria-hidden className="size-4" />
            </span>
            <span className="font-display text-base font-semibold">Dinevo</span>
          </div>
          <button
            type="button"
            onClick={() => void signOut()}
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-muted-foreground hover:text-foreground"
          >
            <LogOut aria-hidden className="size-4" /> Logout
          </button>
        </div>
        <nav className="no-scrollbar flex gap-1 overflow-x-auto px-3 pb-2">
          {NAV.map((item) => (
            <Link key={item.to} to={item.to} className={navClass(isActive(item.to, item.end))}>
              {item.label}
            </Link>
          ))}
        </nav>
      </header>

      <main className="p-4 sm:p-6 lg:ml-64 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
}
