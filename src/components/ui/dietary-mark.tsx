import { cn } from "@/lib/utils";
import type { DietaryType } from "@/types";

const LABEL: Record<DietaryType, string> = {
  VEG: "Vegetarian",
  NON_VEG: "Non-vegetarian",
  EGG: "Contains egg",
};

export function DietaryMark({
  dietary,
  className,
}: {
  dietary?: DietaryType | undefined;
  className?: string;
}) {
  if (!dietary) return null;
  const isVeg = dietary === "VEG";
  return (
    <span
      title={LABEL[dietary]}
      aria-label={LABEL[dietary]}
      className={cn(
        "inline-flex size-4 shrink-0 items-center justify-center rounded-[3px] border-2 bg-card",
        isVeg ? "border-veg" : "border-nonveg",
        className,
      )}
    >
      <span
        aria-hidden
        className={cn("size-1.5 rounded-full", isVeg ? "bg-veg" : "bg-nonveg")}
      />
    </span>
  );
}
