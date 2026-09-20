import { createFileRoute, Link } from "@tanstack/react-router";
import { ScanLine, Sparkles, UtensilsCrossed } from "lucide-react";

const TITLE =
  "Dinevo Dine AR — restaurant menus with dish photography and 3D / AR";
const DESCRIPTION =
  "Dinevo turns a restaurant menu into an immersive experience with real dish photography and 3D / AR dish previews.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: TITLE },
      { name: "description", content: DESCRIPTION },
      { property: "og:title", content: TITLE },
      { property: "og:description", content: DESCRIPTION },
    ],
  }),
  component: LandingPage,
});

/**
 * SaaS landing page. Customers manage their restaurant through the owner
 * dashboard; guests reach a specific menu via that restaurant's QR/slug link.
 */
function LandingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-6 py-16">
      <span className="flex size-12 items-center justify-center rounded-full bg-surface-strong text-background">
        <UtensilsCrossed aria-hidden className="size-6" />
      </span>
      <p className="eyebrow mt-6">Dinevo Dine AR</p>
      <h1 className="mt-3 font-display text-4xl leading-[1.05] sm:text-5xl">
        Your restaurant menu, in 3D and AR.
      </h1>
      <p className="mt-4 leading-relaxed text-muted-foreground">
        Create your restaurant profile, add dishes with real photography, and
        share one QR code that opens your menu instantly.
      </p>

      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <Link
          to="/signup"
          className="inline-flex items-center justify-center rounded-full bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground shadow-lift"
        >
          Create your restaurant
        </Link>
        <Link
          to="/login"
          className="inline-flex items-center justify-center rounded-full border border-border bg-card px-6 py-3.5 text-sm font-semibold hover:bg-secondary"
        >
          Sign in
        </Link>
        <Link
          to="/t/$token"
          params={{ token: "dscape-grand-hotel" }}
          className="inline-flex items-center justify-center rounded-full border border-border bg-card px-6 py-3.5 text-sm font-semibold hover:bg-secondary"
        >
          View Hotel Menu
        </Link>
      </div>

      <ul className="mt-8 space-y-3 text-sm">
        <li className="flex items-start gap-3">
          <ScanLine aria-hidden className="mt-0.5 size-4 shrink-0" />
          Guests scan your restaurant's QR code to open the menu.
        </li>
        <li className="flex items-start gap-3">
          <Sparkles aria-hidden className="mt-0.5 size-4 shrink-0" />
          Every dish has a photo, and selected dishes open in 3D or AR.
        </li>
      </ul>
    </main>
  );
}
