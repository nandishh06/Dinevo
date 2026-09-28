import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Box, Sparkles, UtensilsCrossed } from "lucide-react";
import { MenuQrCode } from "@/components/qr/MenuQrCode";
import { DietaryMark } from "@/components/ui/dietary-mark";
import { DishImage } from "@/components/ui/dish-image";
import { formatPrice } from "@/lib/utils/format";
import type { DietaryType } from "@/types";

const TITLE =
  "Dinevo Dine AR — restaurant menus with dish photography and 3D / AR";
const DESCRIPTION =
  "Dinevo turns a restaurant menu into an immersive experience with real dish photography and 3D / AR dish previews.";

/** The example menu already published by the product. Guests reach it by QR or slug. */
const DEMO_SLUG = "dscape-grand-hotel";
const DEMO_NAME = "Dscape Grand Hotel";

interface SpecimenDish {
  name: string;
  price: number;
  image: string;
  dietary: DietaryType;
}

/** Dishes below are on that live menu, exactly as stored by the product. */
const HERO_DISH: SpecimenDish = {
  name: "Butter Chicken",
  price: 499,
  image: "/images/dishes/butter-chicken.jpg",
  dietary: "NON_VEG",
};

const MENU_SAMPLE: SpecimenDish[] = [
  {
    name: "Paneer Tikka",
    price: 299,
    image: "/images/dishes/paneer-tikka.jpg",
    dietary: "VEG",
  },
  {
    name: "Butter Chicken",
    price: 499,
    image: "/images/dishes/butter-chicken.jpg",
    dietary: "NON_VEG",
  },
  {
    name: "Gulab Jamun",
    price: 149,
    image: "/images/dishes/gulab-jamun.jpg",
    dietary: "VEG",
  },
];

const OWNER_STEPS = [
  {
    title: "Create your restaurant",
    body: "Name it, add the address and phone guests look for. Your menu gets one address and one QR code.",
  },
  {
    title: "Add dishes with photographs",
    body: "Each dish carries its photograph, price, description, dietary mark and availability. A dish you mark unavailable stays on the menu, clearly unavailable.",
  },
  {
    title: "Share one QR code",
    body: "Guests scan it and the live menu opens in the browser. Changes you save are on the next visit.",
  },
];

const FEATURES = [
  {
    title: "A digital menu, not a PDF",
    body: "One address per restaurant, built from your categories and dishes. Guests search it and filter by category on their own phone.",
    note: "Menu, category and dish pages are all served from the same data you maintain.",
  },
  {
    title: "Dish photography that carries the page",
    body: "Every dish holds one photograph. Upload it once and it appears on the menu card, the dish page and as the still image behind the 3D preview.",
    note: "Images are served from storage, sized to the card, and lazy-loaded further down the menu.",
  },
  {
    title: "3D models, only where they earn it",
    body: "Dishes with a model get a 3D / AR marker. The model loads on the preview screen alone, so browsing the rest of the menu stays fast.",
    note: "Optional per dish. A dish without a model keeps its photograph and details.",
  },
  {
    title: "WebAR, no app to install",
    body: "Guests place the dish on their own table through the browser camera. Where AR is not supported, the same screen gives a rotatable 3D preview.",
    note: "Runs in the browser; nothing to download before the dish appears.",
  },
];

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

function LandingPage() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main>
        <Hero />
        <GuestJourney />
        <OwnerSteps />
        <Features />
        <ClosingCta />
      </main>
      <SiteFooter />
    </div>
  );
}

function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex size-9 items-center justify-center rounded-full bg-surface-strong text-background">
            <UtensilsCrossed aria-hidden className="size-5" />
          </span>
          <span className="font-display text-lg font-semibold">Dinevo</span>
        </Link>

        <nav
          aria-label="Sections"
          className="hidden items-center gap-6 text-sm font-semibold text-muted-foreground md:flex"
        >
          <a href="#journey" className="hover:text-foreground">
            Guest journey
          </a>
          <a href="#owners" className="hover:text-foreground">
            For owners
          </a>
          <a href="#features" className="hover:text-foreground">
            Features
          </a>
        </nav>

        <nav aria-label="Account" className="flex items-center gap-1">
          <Link
            to="/login"
            className="rounded-full px-3 py-2 text-sm font-semibold text-muted-foreground hover:bg-secondary hover:text-foreground sm:px-4"
          >
            Sign in
          </Link>
          <Link
            to="/signup"
            className="rounded-full bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground sm:px-4"
          >
            Create account
          </Link>
        </nav>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section aria-labelledby="hero-heading" className="border-b border-border">
      <div className="mx-auto grid max-w-6xl items-center gap-9 px-4 py-12 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-12 lg:py-20">
        <div className="animate-rise">
          <p className="eyebrow">Dinevo Dine AR</p>
          <h1
            id="hero-heading"
            className="mt-4 font-display text-[2.5rem] leading-[1.04] tracking-[-0.02em] sm:text-[3.5rem]"
          >
            Your menu, plated properly.
          </h1>
          <p className="mt-5 max-w-[56ch] text-[0.975rem] leading-relaxed text-muted-foreground sm:text-base">
            Dinevo is a digital menu for restaurants: real dish photography,
            clear dietary detail, and 3D models that open in augmented reality
            on your guest&apos;s own table, straight from the browser.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              to="/signup"
              className="inline-flex items-center justify-center rounded-full bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground shadow-lift transition-transform duration-150 active:scale-[0.98]"
            >
              Create your restaurant
            </Link>
            <Link
              to="/t/$token"
              params={{ token: DEMO_SLUG }}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-6 py-3.5 text-sm font-semibold hover:bg-secondary"
            >
              See a live menu
              <ArrowRight aria-hidden className="size-4" />
            </Link>
          </div>

          <p className="mt-4 text-sm text-muted-foreground">
            No app for guests, no ordering, no accounts for diners. Just the
            menu, done well.
          </p>
        </div>

        {/* The product as proof: one dish, treated the way the menu treats it. */}
        <figure className="animate-rise">
          <div className="overflow-hidden rounded-3xl shadow-lift">
            <DishImage
              src={HERO_DISH.image}
              alt={`${HERO_DISH.name}, as photographed for the menu`}
              priority
              className="aspect-[4/3] w-full"
            />
          </div>
          <figcaption className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <DietaryMark dietary={HERO_DISH.dietary} />
            <span className="font-semibold">{HERO_DISH.name}</span>
            <span aria-hidden className="text-border">
              /
            </span>
            <span className="font-display font-semibold">
              {formatPrice(HERO_DISH.price)}
            </span>
            <span className="text-muted-foreground">
              from the live {DEMO_NAME} menu
            </span>
          </figcaption>
        </figure>
      </div>
    </section>
  );
}

function GuestJourney() {
  return (
    <section
      id="journey"
      aria-labelledby="journey-heading"
      className="scroll-mt-16 border-b border-border bg-surface"
    >
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:py-20">
        <p className="eyebrow">The guest journey</p>
        <h2
          id="journey-heading"
          className="mt-3 max-w-[30ch] font-display text-3xl tracking-[-0.02em] sm:text-4xl"
        >
          Scan, browse, then look closer.
        </h2>

        <ol className="mt-10 grid gap-8 md:grid-cols-3 md:gap-6">
          <li className="md:border-t md:border-border md:pt-6">
            <p className="font-display text-sm font-semibold text-muted-foreground">
              01
            </p>
            <h3 className="mt-2 font-display text-xl">Scan the code</h3>
            <p className="mt-2 max-w-[42ch] text-sm leading-relaxed text-muted-foreground">
              One QR code per restaurant. Printed on the table, the door or the
              bill, it opens the live menu in the phone&apos;s browser.
            </p>
            <div className="mt-5 max-w-[220px]">
              <MenuQrCode path={`/t/${DEMO_SLUG}`} size={148} />
            </div>
          </li>

          <li className="md:border-t md:border-border md:pt-6">
            <p className="font-display text-sm font-semibold text-muted-foreground">
              02
            </p>
            <h3 className="mt-2 font-display text-xl">Browse the dishes</h3>
            <p className="mt-2 max-w-[42ch] text-sm leading-relaxed text-muted-foreground">
              Photographs first, then the price, dietary mark and description.
              Search and category filters move through the whole menu.
            </p>
            <ul className="mt-5 space-y-3">
              {MENU_SAMPLE.map((dish) => (
                <li key={dish.name} className="flex items-center gap-3">
                  <DishImage
                    src={dish.image}
                    alt={dish.name}
                    className="size-14 shrink-0 rounded-xl object-cover"
                  />
                  <span className="min-w-0">
                    <span className="flex items-center gap-1.5 text-sm font-semibold">
                      <DietaryMark dietary={dish.dietary} />
                      <span className="truncate">{dish.name}</span>
                    </span>
                    <span className="font-display text-sm text-muted-foreground">
                      {formatPrice(dish.price)}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </li>

          <li className="md:border-t md:border-border md:pt-6">
            <p className="font-display text-sm font-semibold text-muted-foreground">
              03
            </p>
            <h3 className="mt-2 font-display text-xl">See it in 3D or AR</h3>
            <p className="mt-2 max-w-[42ch] text-sm leading-relaxed text-muted-foreground">
              On a dish page, guests can rotate a 3D model or place the dish on
              the table in front of them with the camera.
            </p>
            <div className="mt-5 space-y-3">
              <span className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground">
                <Sparkles aria-hidden className="size-4" />
                View in AR
              </span>
              <span className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-border bg-card px-6 py-3.5 text-sm font-semibold">
                <Box aria-hidden className="size-4" />
                View 3D
              </span>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              Shown as they appear on a dish page. AR uses the browser camera.
            </p>
          </li>
        </ol>
      </div>
    </section>
  );
}

function OwnerSteps() {
  return (
    <section
      id="owners"
      aria-labelledby="owners-heading"
      className="scroll-mt-16 border-b border-border"
    >
      <div className="mx-auto grid max-w-6xl gap-9 px-4 py-12 sm:px-6 lg:grid-cols-2 lg:gap-16 lg:py-20">
        <div>
          <p className="eyebrow">For restaurant owners</p>
          <h2
            id="owners-heading"
            className="mt-3 max-w-[26ch] font-display text-3xl tracking-[-0.02em] sm:text-4xl"
          >
            Three steps, then it runs itself.
          </h2>
          <p className="mt-4 max-w-[52ch] leading-relaxed text-muted-foreground">
            The dashboard holds the restaurant, the categories and the dishes.
            What you save is what guests see.
          </p>
        </div>

        <ol className="divide-y divide-border border-t border-border">
          {OWNER_STEPS.map((step, index) => (
            <li key={step.title} className="flex gap-5 py-5">
              <span className="font-display text-sm font-semibold text-muted-foreground">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <h3 className="font-display text-xl">{step.title}</h3>
                <p className="mt-1 max-w-[52ch] text-sm leading-relaxed text-muted-foreground">
                  {step.body}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Features() {
  return (
    <section
      id="features"
      aria-labelledby="features-heading"
      className="scroll-mt-16 border-b border-border bg-surface"
    >
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:py-20">
        <p className="eyebrow">What is in the product today</p>
        <h2
          id="features-heading"
          className="mt-3 max-w-[34ch] font-display text-3xl tracking-[-0.02em] sm:text-4xl"
        >
          Four things, done carefully.
        </h2>

        <ul className="mt-10 divide-y divide-border border-t border-border">
          {FEATURES.map((feature) => (
            <li
              key={feature.title}
              className="grid gap-2 py-6 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.4fr)] md:gap-10"
            >
              <h3 className="font-display text-xl md:text-2xl">
                {feature.title}
              </h3>
              <div>
                <p className="max-w-[62ch] leading-relaxed text-muted-foreground">
                  {feature.body}
                </p>
                <p className="mt-2 max-w-[62ch] text-sm text-muted-foreground/80">
                  {feature.note}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function ClosingCta() {
  return (
    <section
      aria-labelledby="closing-heading"
      className="border-b border-border"
    >
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:py-20">
        <h2
          id="closing-heading"
          className="max-w-[24ch] font-display text-3xl leading-[1.1] tracking-[-0.02em] sm:text-5xl"
        >
          Put your menu where guests already are.
        </h2>
        <p className="mt-5 max-w-[56ch] leading-relaxed text-muted-foreground">
          One restaurant, one menu, one code. Start with the dishes you serve
          today.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link
            to="/signup"
            className="inline-flex items-center justify-center rounded-full bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground shadow-lift transition-transform duration-150 active:scale-[0.98]"
          >
            Create your restaurant
          </Link>
          <Link
            to="/t/$token"
            params={{ token: DEMO_SLUG }}
            className="inline-flex items-center justify-center rounded-full border border-border bg-card px-6 py-3.5 text-sm font-semibold hover:bg-secondary"
          >
            See a live menu
          </Link>
        </div>
      </div>
    </section>
  );
}

function SiteFooter() {
  return (
    <footer className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-8 text-sm text-muted-foreground sm:px-6">
      <span className="flex items-center gap-2">
        <span className="flex size-7 items-center justify-center rounded-full bg-surface-strong text-background">
          <UtensilsCrossed aria-hidden className="size-4" />
        </span>
        Dinevo Dine AR
      </span>
      <nav aria-label="Footer" className="flex flex-wrap items-center gap-5">
        <Link
          to="/t/$token"
          params={{ token: DEMO_SLUG }}
          className="hover:text-foreground"
        >
          Example menu
        </Link>
        <Link to="/login" className="hover:text-foreground">
          Sign in
        </Link>
        <Link to="/signup" className="hover:text-foreground">
          Create account
        </Link>
      </nav>
    </footer>
  );
}
