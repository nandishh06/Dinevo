import { createElement, useEffect, useRef, useState } from "react";
import { Camera } from "lucide-react";
import { CameraArView } from "@/components/ar/CameraArView";
import {
  isArCapable,
  loadArRuntime,
  usdzUrlFor,
  type ArRuntimeStatus,
} from "@/lib/ar/runtime";

export interface DishARViewerProps {
  modelUrl?: string | undefined;
  dishName: string;
  imageUrl: string;
  posterUrl?: string | undefined;
  /** "ar" opens AR placement with the same model; "3d" shows the interactive preview. */
  mode?: "3d" | "ar";
}

/**
 * The single AR/3D boundary in the app.
 *
 * Both experiences share the SAME model asset when a valid modelUrl exists:
 *  - mode "ar"  → <model-viewer> with AR enabled (GLB + ios-src USDZ) for
 *                 native/WebAR placement.
 *  - mode "3d"  → the same <model-viewer> as an interactive 3D preview.
 *
 * When no valid modelUrl exists, "ar" falls back to image-based AR through
 * CameraArView (the canonical dish photograph over the live camera).
 *
 * The GLB is fetched only when a modelUrl is present (explicit user intent).
 */
export function DishARViewer({
  modelUrl,
  dishName,
  imageUrl,
  posterUrl,
  mode = "3d",
}: DishARViewerProps) {
  const [status, setStatus] = useState<ArRuntimeStatus>("idle");
  const [cameraOpen, setCameraOpen] = useState(false);
  const viewerRef = useRef<HTMLElement | null>(null);
  const arCapable = isArCapable();

  useEffect(() => {
    if (!modelUrl) return;
    let cancelled = false;
    setStatus("loading");
    void loadArRuntime(modelUrl).then((next) => {
      if (!cancelled) setStatus(next);
    });
    return () => {
      cancelled = true;
    };
  }, [modelUrl]);

  // Image AR fallback: no valid model → canonical photo over live camera.
  const cameraLayer = cameraOpen ? (
    <CameraArView
      dishName={dishName}
      imageUrl={imageUrl}
      onClose={() => setCameraOpen(false)}
    />
  ) : null;

  // No model at all → image-based AR only.
  if (!modelUrl) {
    return (
      <div className="surface-card overflow-hidden">
        <div className="relative aspect-square overflow-hidden bg-surface">
          <img
            key={imageUrl}
            src={imageUrl}
            alt={dishName}
            className="size-full object-cover opacity-90"
          />
        </div>
        <button
          type="button"
          onClick={() => setCameraOpen(true)}
          className="flex w-full items-center justify-center gap-2 border-t border-border px-4 py-3 text-sm font-semibold text-foreground"
        >
          <Camera aria-hidden className="size-4" />
          View in AR — place {dishName} on your table
        </button>
        {cameraLayer}
      </div>
    );
  }

  if (status === "missing-asset" || status === "unsupported") {
    // Model URL present but asset missing → image AR fallback.
    return (
      <div className="surface-card overflow-hidden">
        <div className="relative aspect-square overflow-hidden bg-surface">
          <img
            key={imageUrl}
            src={imageUrl}
            alt={dishName}
            className="size-full object-cover opacity-90"
          />
        </div>
        <button
          type="button"
          onClick={() => setCameraOpen(true)}
          className="flex w-full items-center justify-center gap-2 border-t border-border px-4 py-3 text-sm font-semibold text-foreground"
        >
          <Camera aria-hidden className="size-4" />
          View in AR — place {dishName} on your table
        </button>
        {cameraLayer}
      </div>
    );
  }

  return (
    <div className="surface-card relative overflow-hidden bg-surface">
      {status === "loading" ? (
        <div className="flex aspect-square items-center justify-center">
          {posterUrl ? (
            <img
              src={posterUrl}
              alt=""
              aria-hidden
              className="absolute inset-0 size-full scale-105 object-cover opacity-25 blur-sm"
            />
          ) : null}
          <p className="relative z-10 font-display text-lg font-semibold">
            Preparing {dishName} in 3D…
          </p>
        </div>
      ) : (
        <div className="aspect-square w-full">
          {createElement("model-viewer", {
            ref: viewerRef,
            src: modelUrl,
            poster: posterUrl,
            alt: `3D model of ${dishName}`,
            ar: mode === "ar" && arCapable ? true : undefined,
            "ar-modes": "webxr scene-viewer quick-look",
            "ar-placement": "floor",
            "ios-src": usdzUrlFor(modelUrl),
            "camera-controls": true,
            "touch-action": "pan-y",
            "shadow-intensity": "1",
            "environment-image": "neutral",
            "auto-rotate": true,
            style: { width: "100%", height: "100%" },
          })}
        </div>
      )}
    </div>
  );
}
