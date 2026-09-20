import { useEffect, useRef, useState } from "react";
import { Download } from "lucide-react";

/**
 * Renders the single, general restaurant QR code.
 * Generated in the browser only — nothing is fetched during SSR.
 */
export function MenuQrCode({
  path,
  size = 208,
  downloadName,
}: {
  path: string;
  size?: number;
  downloadName?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    setUrl(`${window.location.origin}${path}`);
  }, [path]);

  useEffect(() => {
    if (!url || !canvasRef.current) return;
    let cancelled = false;
    void import("qrcode").then(({ default: QRCode }) => {
      if (cancelled || !canvasRef.current) return;
      void QRCode.toCanvas(canvasRef.current, url, {
        width: size,
        margin: 1,
        color: { dark: "#2b1d16", light: "#ffffff" },
      });
    });
    return () => {
      cancelled = true;
    };
  }, [url, size]);

  function downloadQr() {
    const canvas = canvasRef.current;
    if (!canvas || !downloadName) return;
    const link = document.createElement("a");
    link.download = downloadName;
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  return (
    <figure className="surface-card flex flex-col items-center gap-3 p-5">
      <canvas
        ref={canvasRef}
        width={size}
        height={size}
        role="img"
        aria-label="QR code that opens the Dinevo menu"
        className="rounded-xl bg-white"
      />
      {downloadName ? (
        <button
          type="button"
          onClick={downloadQr}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 text-sm font-semibold hover:bg-secondary"
        >
          <Download aria-hidden className="size-4" />
          Save QR
        </button>
      ) : null}
      <figcaption className="text-center text-xs break-all text-muted-foreground">
        {url ?? path}
      </figcaption>
    </figure>
  );
}
