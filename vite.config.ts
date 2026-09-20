import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import viteTsConfigPaths from "vite-tsconfig-paths";
import { nitro } from "nitro/vite";

// Dscape-owned Vite configuration.
//
// The build pipeline is fully owned by the project:
//   - tanstackStart: TanStack Start SSR + file routing
//   - viteReact: React fast refresh / JSX
//   - tailwindcss: Tailwind v4 styles
//   - viteTsConfigPaths: @/* alias -> ./src/*
//   - nitro: production server output (SSR, nested routes, static assets)
//
// Nitro's Vercel preset makes `bun run build` emit a ready-to-deploy .output
// for Vercel. Swap the preset here if the hosting target changes.
export default defineConfig({
  plugins: [
    tanstackStart({
      // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
      // nitro/vite builds from this.
      server: { entry: "server" },
    }),
    viteReact(),
    tailwindcss(),
    viteTsConfigPaths(),
    nitro({
      preset: "vercel",
      // Vercel Build Output API: guarantee .glb / .usdz static assets are
      // served with the correct model content types regardless of the
      // platform's default mime map. Merged into .vercel/output/config.json
      // by Nitro.
      vercel: {
        config: {
          version: 3,
          overrides: {
            "models/dishes/*.glb": {
              contentType: "model/gltf-binary",
            },
            "models/dishes/*.usdz": {
              contentType: "model/vnd.usdz+zip",
            },
          },
        },
      },
    }),
  ],
  server: {
    host: "0.0.0.0",
    https: {
      key: "./.certs/dscape-key.pem",
      cert: "./.certs/dscape-cert.pem",
    },
  },
});
