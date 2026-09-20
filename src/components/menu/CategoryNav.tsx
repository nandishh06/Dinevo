import { cn } from "@/lib/utils";
import type { Category } from "@/types";

export function CategoryNav({
  categories,
  activeId,
  onSelect,
}: {
  categories: Category[];
  activeId: string;
  onSelect: (id: string) => void;
}) {
  const options = [{ id: "all", name: "All", sortOrder: 0 }, ...categories];
  return (
    <nav aria-label="Menu categories" className="sticky top-[68px] z-20 bg-background/90 backdrop-blur-md">
      <ul className="no-scrollbar flex gap-2 overflow-x-auto px-4 py-3 sm:px-6">
        {options.map((c) => {
          const isActive = c.id === activeId;
          return (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => onSelect(c.id)}
                aria-current={isActive ? "true" : undefined}
                className={cn(
                  "rounded-full border px-4 py-2 text-sm font-semibold whitespace-nowrap transition-all duration-200",
                  isActive
                    ? "border-transparent bg-surface-strong text-background shadow-card"
                    : "border-border bg-card text-muted-foreground hover:text-foreground",
                )}
              >
                {c.name}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
