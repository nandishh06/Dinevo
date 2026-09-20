import { Search, X } from "lucide-react";

export function MenuSearch({
  value,
  onChange,
}: {
  value: string;
  onChange: (next: string) => void;
}) {
  return (
    <div className="relative">
      <label htmlFor="menu-search" className="sr-only">
        Search the menu
      </label>
      <Search
        aria-hidden
        className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-muted-foreground"
      />
      <input
        id="menu-search"
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search biryani, paneer, chicken…"
        className="w-full rounded-full border border-border bg-card py-3 pr-10 pl-11 text-sm shadow-card outline-none placeholder:text-muted-foreground focus-visible:border-ring"
      />
      {value ? (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Clear search"
          className="absolute top-1/2 right-3 -translate-y-1/2 rounded-full p-1.5 text-muted-foreground hover:bg-secondary"
        >
          <X aria-hidden className="size-4" />
        </button>
      ) : null}
    </div>
  );
}
