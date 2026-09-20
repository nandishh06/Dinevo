# Dscape Dine AR

QR-driven hotel and restaurant menu with real dish photography and 3D / AR dish
previews. A customer scans one printed QR code, opens the hotel menu, browses
photographed dishes, and can view selected dishes as a real 3D model — in a
viewer or placed on their own table through camera AR.

## Product flow (Phase 1)

```
PHYSICAL RESTAURANT QR
  → /t/menu
  → Hotel / restaurant menu
  → Featured dishes + full menu
  → Dish detail (photo first)
  → 3D preview
  → WebAR (camera placement)
```

Phase 1 intentionally excludes ordering, cart, billing, payment, kitchen
dashboard, and customer order history.

## Stack

- TanStack Start (SSR) + TanStack Router
- React 19, TypeScript (strict)
- Tailwind CSS v4
- `@google/model-viewer` (lazy-loaded) for 3D / AR
- `qrcode` for runtime QR generation
- Nitro build output — Vercel preset

## Development

Requires Node.js + npm, or bun (bun.lock is committed).

```sh
bun install
bun run dev        # local dev server
bun run build      # production build (Nitro .output/)
bun run preview    # serve the production build locally
```

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Landing page: prints the general restaurant QR code |
| `/t/menu` | General venue menu |
| `/t/demo-table-17` | Demo table-scoped token (future phases) |
| `/t/$token/dish/$dishId` | Dish detail |
| `/t/$token/ar/$dishId` | 3D / AR preview (`?mode=3d` or `?mode=ar`) |

## Data

Phase 1 uses a mock dataset (`src/data/mock/`) behind a single API seam
(`src/lib/api/`). The adapter is swapped for an HTTP implementation against the
future FastAPI backend without touching UI code. See the documented contract in
`src/lib/api/index.ts`.

3D models are lazy-loaded: a `.glb` in `public/models/dishes/` matching the
dish's `modelUrl` is fetched only when the guest opens the 3D / AR screen.

## Deployment

The production build targets Vercel (Nitro `vercel` preset in `vite.config.ts`).
HTTPS is required for camera access. Deep links and nested routes are SSR-rendered.
