export type ArRuntimeStatus =
  | "idle"
  | "loading"
  | "ready"
  | "missing-asset"
  | "unsupported";

/**
 * Coarse capability probe for placing a model in the real world.
 * Scene-viewer (Android) and Quick Look (iOS) are handled by <model-viewer>;
 * this only decides whether we advertise the AR button.
 */
export function isArCapable(): boolean {
  if (typeof window === "undefined") return false;
  if ("xr" in navigator) return true;
  return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

let runtimePromise: Promise<void> | null = null;

/**
 * Loads the <model-viewer> custom element exactly once, on demand.
 * Nothing here runs while the guest browses the menu.
 */
export function loadModelViewer(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  runtimePromise ??= import("@google/model-viewer").then(() => undefined);
  return runtimePromise;
}

/** Verifies the GLB actually exists before handing it to the viewer. */
export async function probeModelAsset(modelUrl: string): Promise<boolean> {
  try {
    const response = await fetch(modelUrl, { method: "HEAD" });
    const type = response.headers.get("content-type") ?? "";
    return response.ok && !type.includes("text/html");
  } catch {
    return false;
  }
}

/** Lazy resolution used by <DishARViewer>: probe asset, then boot the runtime. */
export async function loadArRuntime(modelUrl: string): Promise<ArRuntimeStatus> {
  const exists = await probeModelAsset(modelUrl);
  if (!exists) return "missing-asset";
  try {
    await loadModelViewer();
    return "ready";
  } catch {
    return "unsupported";
  }
}

/**
 * iOS AR delivery asset derived from the GLB.
 *
 * Native iOS AR (Quick Look / ARKit) needs a USDZ. The convention is a
 * sibling file with the same name and a `.usdz` extension — e.g.
 * `/models/dishes/chicken-biryani.glb` -> `/models/dishes/chicken-biryani.usdz`.
 * Returns null when the model URL doesn't follow that convention; model-viewer
 * then falls back to its other AR modes (scene-viewer / webxr).
 */
export function usdzUrlFor(modelUrl: string | undefined): string | null {
  if (!modelUrl) return null;
  if (!modelUrl.endsWith(".glb")) return null;
  return `${modelUrl.slice(0, -4)}.usdz`;
}
