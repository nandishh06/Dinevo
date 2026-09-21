import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import viteTsConfigPaths from "vite-tsconfig-paths";
import { nitro } from "nitro/vite";

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
