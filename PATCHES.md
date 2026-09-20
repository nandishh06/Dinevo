# Node patches applied to `node_modules`

These small patches fix framework bugs that are not yet released upstream.
They are applied directly to the installed package files and will be **lost on
the next `bun install`** — reapply after reinstalling dependencies.

## 1. `@tanstack/router-core` — SSR stream lifetime watchdog closes (not errors)

**Files:**
- `node_modules/@tanstack/router-core/dist/esm/ssr/transformStreamWithRouter.js`
- `node_modules/@tanstack/router-core/dist/cjs/ssr/transformStreamWithRouter.cjs`

**Problem:** When a client aborts a request mid-SSR, the dev-server adapter
does not always cancel the SSR stream. The stream idles until the 120s lifetime
watchdog fires, and the watchdog calls `controller.error(...)` on a stream that
may no longer have a consumer — an unhandled `'error'` that can take down the
dev server (TanStack router issue #7748).

**Change (matches upstream PR #7909, not yet released):** in both watchdog
`setTimeout` handlers, replace `safeError(err); cleanup(err);` with
`safeClose(); cleanup();`. The warning stays (it is a leak-prevention
fallback), but the stream is closed cleanly instead of erroring, so the dev
server can never crash on an abandoned stream.

**Reapply:** replace
```js
lifetimeTimeoutHandle = setTimeout(() => {
  if (!cleanedUp && !isDone()) {
    const err = /* @__PURE__ */ new Error("Stream lifetime exceeded");
    console.warn(`SSR stream transform exceeded maximum lifetime (${lifetimeMs}ms), forcing cleanup`);
    safeError(err);
    cleanup(err);
  }
}, lifetimeMs);
```
with
```js
lifetimeTimeoutHandle = setTimeout(() => {
  if (!cleanedUp && !isDone()) {
    console.warn(`SSR stream transform exceeded maximum lifetime (${lifetimeMs}ms), forcing cleanup`);
    safeClose();
    cleanup();
  }
}, lifetimeMs);
```
in both `dist/esm` and `dist/cjs` copies.

## Notes

- **Production is unaffected**: the Vercel/Nitro node-server aborts request
  signals on client disconnect correctly; the SSR lifetime watchdog never fires
  in the production build.
- The repeated dev warning is a symptom of aborted SSR requests (rapid
  navigation, hover preloads aborted, phone dropping the LAN connection) while
  developing over a slow connection. It is harmless after the patch (server
  stays healthy) and does not occur in production.
