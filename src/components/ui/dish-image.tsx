import { useEffect, useState } from "react";
import { ImageOff } from "lucide-react";
import { cn } from "@/lib/utils";

interface DishImageProps {
  src: string;
  alt: string;
  className?: string;
  priority?: boolean;
  sizes?: string;
}

/** Image with graceful fallback — a missing asset must never break the menu. */
export function DishImage({ src, alt, className, priority = false }: DishImageProps) {
  const [failed, setFailed] = useState(false);

  // Reset the failure state when the source changes so a later dish's image
  // isn't stuck behind a previous dish's error fallback.
  useEffect(() => {
    setFailed(false);
  }, [src]);

  if (failed) {
    return (
      <div
        role="img"
        aria-label={`${alt} — image unavailable`}
        className={cn(
          "flex items-center justify-center bg-surface text-muted-foreground",
          className,
        )}
      >
        <ImageOff aria-hidden className="size-6 opacity-60" />
      </div>
    );
  }

  return (
    <img
      key={src}
      src={src}
      alt={alt}
      loading={priority ? "eager" : "lazy"}
      decoding="async"
      fetchPriority={priority ? "high" : "auto"}
      onError={() => setFailed(true)}
      className={cn("object-cover", className)}
    />
  );
}
