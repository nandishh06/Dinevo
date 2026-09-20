import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, Move, RotateCcw, X, ZoomIn, ZoomOut } from "lucide-react";

export interface CameraArViewProps {
  dishName: string;
  imageUrl: string;
  onClose: () => void;
}

type CameraState = "starting" | "live" | "denied" | "unavailable";

/**
 * Live-camera AR: opens the rear camera and composites the dish's canonical
 * photograph on top of the real-world feed. The guest points the phone at the
 * table and drags/pinches to place the plate. This is the PRIMARY AR
 * experience and always uses the dish image — never the 3D model.
 */
export function CameraArView({ dishName, imageUrl, onClose }: CameraArViewProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [camera, setCamera] = useState<CameraState>("starting");
  const [pos, setPos] = useState({ x: 0.5, y: 0.68 });
  const [scale, setScale] = useState(1);
  const dragRef = useRef<{ active: boolean; pinchStart?: number | undefined; scaleStart?: number | undefined }>({
    active: false,
  });

  // Camera stream (rear-facing when available).
  useEffect(() => {
    let cancelled = false;
    const media = typeof navigator !== "undefined" ? navigator.mediaDevices : undefined;
    if (!media?.getUserMedia) {
      setCamera("unavailable");
      return;
    }
    void media
      .getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          void videoRef.current.play().catch(() => undefined);
        }
        setCamera("live");
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const name = (error as { name?: string })?.name;
        setCamera(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "unavailable");
      });
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, []);

  const moveTo = useCallback((clientX: number, clientY: number) => {
    const rect = stageRef.current?.getBoundingClientRect();
    if (!rect) return;
    setPos({
      x: Math.min(0.95, Math.max(0.05, (clientX - rect.left) / rect.width)),
      y: Math.min(0.95, Math.max(0.05, (clientY - rect.top) / rect.height)),
    });
  }, []);

  const onPointerDown = (event: React.PointerEvent) => {
    dragRef.current.active = true;
    (event.target as Element).setPointerCapture?.(event.pointerId);
    moveTo(event.clientX, event.clientY);
  };
  const onPointerMove = (event: React.PointerEvent) => {
    if (!dragRef.current.active) return;
    moveTo(event.clientX, event.clientY);
  };
  const endDrag = () => {
    dragRef.current.active = false;
  };

  const onTouchMove = (event: React.TouchEvent) => {
    if (event.touches.length !== 2) return;
    const [a, b] = [event.touches[0]!, event.touches[1]!];
    const distance = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
    if (dragRef.current.pinchStart == null) {
      dragRef.current.pinchStart = distance;
      dragRef.current.scaleStart = scale;
      return;
    }
    const next = (dragRef.current.scaleStart ?? 1) * (distance / dragRef.current.pinchStart);
    setScale(Math.min(2.5, Math.max(0.4, next)));
  };
  const onTouchEnd = () => {
    dragRef.current.pinchStart = undefined;
  };

  return (
    <div className="fixed inset-0 z-50 bg-black">
      <div
        ref={stageRef}
        className="relative size-full touch-none overflow-hidden"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <video
          ref={videoRef}
          playsInline
          muted
          autoPlay
          className="absolute inset-0 size-full object-cover"
        />

        {camera === "live" ? (
          <div
            className="pointer-events-none absolute"
            style={{
              left: `${pos.x * 100}%`,
              top: `${pos.y * 100}%`,
              width: `${58 * scale}vw`,
              transform: "translate(-50%, -50%)",
            }}
          >
            <img
              key={imageUrl}
              src={imageUrl}
              alt={dishName}
              className="w-full rounded-full object-cover shadow-[0_28px_50px_-12px_rgba(0,0,0,0.75)]"
              style={{ aspectRatio: "1 / 1", transform: "perspective(700px) rotateX(52deg)" }}
            />
          </div>
        ) : null}

        {/* Top bar */}
        <div className="absolute inset-x-0 top-0 flex items-center justify-between p-4">
          <span className="rounded-full bg-black/55 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur">
            {dishName} · live AR
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close AR view"
            className="rounded-full bg-black/55 p-2 text-white backdrop-blur"
          >
            <X aria-hidden className="size-5" />
          </button>
        </div>

        {camera === "starting" ? (
          <div className="absolute inset-0 grid place-items-center bg-black/80 px-8 text-center text-white">
            <p className="flex items-center gap-2 text-sm font-semibold">
              <Camera aria-hidden className="size-5" /> Opening your camera…
            </p>
          </div>
        ) : null}

        {camera === "denied" || camera === "unavailable" ? (
          <div className="absolute inset-0 grid place-items-center bg-black/85 px-8 text-center text-white">
            <div className="max-w-xs space-y-3">
              <Camera aria-hidden className="mx-auto size-8" />
              <p className="font-display text-lg">
                {camera === "denied" ? "Camera access blocked" : "No camera available"}
              </p>
              <p className="text-sm text-white/70">
                {camera === "denied"
                  ? "Allow camera access in your browser settings, then reopen AR to place the dish on your table."
                  : "This device or browser can't open a camera, so AR placement isn't available here."}
              </p>
              <button
                type="button"
                onClick={onClose}
                className="rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-black"
              >
                Back to dish preview
              </button>
            </div>
          </div>
        ) : null}

        {/* Controls */}
        {camera === "live" ? (
          <div className="absolute inset-x-0 bottom-0 space-y-3 p-4">
            <p className="flex items-center justify-center gap-2 rounded-full bg-black/55 px-4 py-2 text-center text-xs text-white backdrop-blur">
              <Move aria-hidden className="size-4" />
              Point at your table, then tap or drag to place {dishName}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                aria-label="Make smaller"
                onClick={() => setScale((s) => Math.max(0.4, s - 0.15))}
                className="rounded-full bg-white/90 p-3 text-black"
              >
                <ZoomOut aria-hidden className="size-5" />
              </button>
              <button
                type="button"
                aria-label="Reset placement"
                onClick={() => {
                  setScale(1);
                  setPos({ x: 0.5, y: 0.68 });
                }}
                className="rounded-full bg-white/90 p-3 text-black"
              >
                <RotateCcw aria-hidden className="size-5" />
              </button>
              <button
                type="button"
                aria-label="Make bigger"
                onClick={() => setScale((s) => Math.min(2.5, s + 0.15))}
                className="rounded-full bg-white/90 p-3 text-black"
              >
                <ZoomIn aria-hidden className="size-5" />
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
