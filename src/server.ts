import "./lib/error-capture";

import { consumeLastCapturedError } from "./lib/error-capture";
import { renderErrorPage } from "./lib/error-page";

type ServerEntry = {
  fetch: (request: Request, env: unknown, ctx: unknown) => Promise<Response> | Response;
};

let serverEntryPromise: Promise<ServerEntry> | undefined;

async function getServerEntry(): Promise<ServerEntry> {
  if (!serverEntryPromise) {
    serverEntryPromise = import("@tanstack/react-start/server-entry").then(
      (m) => (m.default ?? m) as ServerEntry,
    );
  }
  return serverEntryPromise;
}

// h3 swallows in-handler throws into a normal 500 Response with body
// {"unhandled":true,"message":"HTTPError"} — try/catch alone never fires for those.
async function normalizeCatastrophicSsrResponse(response: Response): Promise<Response> {
  if (response.status < 500) return response;
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return response;

  const body = await response.clone().text();
  if (!isH3SwallowedErrorBody(body)) return response;

  console.error(consumeLastCapturedError() ?? new Error(`h3 swallowed SSR error: ${body}`));
  return new Response(renderErrorPage(), {
    status: 500,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

function isH3SwallowedErrorBody(body: string): boolean {
  try {
    const payload = JSON.parse(body) as { unhandled?: unknown; message?: unknown };
    return payload.unhandled === true && payload.message === "HTTPError";
  } catch {
    return false;
  }
}

/**
 * Abort propagation for SSR streams.
 *
 * In dev, a client that disconnects mid-SSR (rapid navigation, phone losing
 * the LAN connection, curl --max-time) does not always cancel the response
 * body stream through the adapter chain. The abandoned stream then idles until
 * router-core's 120s lifetime watchdog fires, spamming:
 *
 *   "SSR stream transform exceeded maximum lifetime (120000ms), forcing cleanup"
 *
 * This wrapper listens on the request signal and cancels the response body the
 * moment the client goes away, so the transform is cleaned up immediately.
 * Applies to both dev and production builds.
 */
function propagateRequestAbortToBody(request: Request, response: Response): Response {
  const signal = request.signal;
  if (signal.aborted) {
    response.body?.cancel().catch(() => undefined);
    return response;
  }
  if (!response.body) return response;
  const onAbort = () => {
    void response.body?.cancel().catch(() => undefined);
  };
  signal.addEventListener("abort", onAbort, { once: true });
  return response;
}

export default {
  async fetch(request: Request, env: unknown, ctx: unknown) {
    try {
      const handler = await getServerEntry();
      const response = await handler.fetch(request, env, ctx);
      return propagateRequestAbortToBody(request, await normalizeCatastrophicSsrResponse(response));
    } catch (error) {
      console.error(error);
      return new Response(renderErrorPage(), {
        status: 500,
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }
  },
};
