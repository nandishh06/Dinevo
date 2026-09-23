import { defineConfig } from "vite";
import { request as httpRequest, type OutgoingHttpHeaders } from "node:http";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import viteTsConfigPaths from "vite-tsconfig-paths";
import { nitro } from "nitro/vite";

export default defineConfig({
  plugins: [
    // Dev-only: the TanStack Start/Nitro dev middleware (registered in
    // configureServer) runs before Vite's built-in `server.proxy` and swallows
    // extensionless /api/* requests. Registering this proxy as the FIRST plugin
    // puts its middleware ahead of Nitro's, so /api/* reaches the FastAPI
    // backend with the /api prefix preserved (FastAPI serves /api/* both locally
    // and in production). Not active for builds.
    {
      name: "dev-api-proxy",
      apply: "serve",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (!req.url?.startsWith("/api/")) return next();
          // Strip HTTP/2 pseudo-headers (:method, :path, :authority, …) — Node's
          // http.request() rejects header names beginning with ":".
          const headers: OutgoingHttpHeaders = {};
          for (const [key, value] of Object.entries(req.headers)) {
            if (key.startsWith(":") || value === undefined) continue;
            headers[key] = value;
          }
          const upstream = httpRequest(
            {
              host: "127.0.0.1",
              port: 8000,
              method: req.method,
              path: req.url,
              headers,
            },
            (upstreamRes) => {
              res.writeHead(upstreamRes.statusCode ?? 502, upstreamRes.headers);
              upstreamRes.pipe(res);
            },
          );
          upstream.on("error", () => {
            res.statusCode = 502;
            res.setHeader("content-type", "text/plain; charset=utf-8");
            res.end("api proxy error");
          });
          req.pipe(upstream);
        });
      },
    },
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
