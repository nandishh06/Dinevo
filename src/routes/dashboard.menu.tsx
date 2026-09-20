import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent } from "react";
import { ChevronDown, ChevronUp, ImagePlus, Plus, X } from "lucide-react";
import { dashboardApi } from "@/lib/api/dashboard";
import type { Category, Dish } from "@/types";

export const Route = createFileRoute("/dashboard/menu")({
  component: MenuPage,
});

interface DishFormState {
  mode: "add" | "edit";
  dish?: Dish;
  name: string;
  description: string;
  price: string;
  categoryId: string;
  isAvailable: boolean;
  imageFile: File | null;
}

function emptyForm(categories: Category[]): DishFormState {
  return {
    mode: "add",
    name: "",
    description: "",
    price: "",
    categoryId: categories[0]?.id ?? "",
    isAvailable: true,
    imageFile: null,
  };
}

function formFromDish(dish: Dish): DishFormState {
  return {
    mode: "edit",
    dish,
    name: dish.name,
    description: dish.description ?? "",
    price: String(dish.price),
    categoryId: dish.categoryId ?? "",
    isAvailable: dish.isAvailable,
    imageFile: null,
  };
}

function MenuPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState("all");

  const categoriesQuery = useQuery({
    queryKey: ["dashboard-categories"],
    queryFn: () => dashboardApi.getCategories(),
  });
  const itemsQuery = useQuery({
    queryKey: ["dashboard-menu-items"],
    queryFn: () => dashboardApi.getMenuItems(),
  });

  const categories = categoriesQuery.data ?? [];
  const items = itemsQuery.data ?? [];

  const visibleItems = useMemo(() => {
    if (selectedCategoryId === "all") return items;
    return items.filter((d) => d.categoryId === selectedCategoryId);
  }, [items, selectedCategoryId]);

  const categoryNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of categories) map.set(c.id, c.name);
    return map;
  }, [categories]);

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["dashboard-categories"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard-menu-items"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
    ]);

  return (
    <div>
      <div>
        <h1 className="font-display text-3xl">Menu</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your categories and dishes.
        </p>
      </div>

      {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-[260px_1fr]">
        <CategoryPanel
          categories={categories}
          items={items}
          selectedId={selectedCategoryId}
          onSelect={setSelectedCategoryId}
          onError={setError}
          onChanged={invalidate}
        />

        <DishPanel
          categories={categories}
          items={visibleItems}
          categoryNameById={categoryNameById}
          onError={setError}
          onChanged={invalidate}
        />
      </div>
    </div>
  );
}

function CategoryPanel({
  categories,
  items,
  selectedId,
  onSelect,
  onError,
  onChanged,
}: {
  categories: Category[];
  items: Dish[];
  selectedId: string;
  onSelect: (id: string) => void;
  onError: (m: string | null) => void;
  onChanged: () => void;
}) {
  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");

  const createMutation = useMutation({
    mutationFn: (n: string) =>
      dashboardApi.createCategory(n, categories.length),
    onSuccess: () => {
      setName("");
      onChanged();
    },
    onError: (e: Error) => onError(e.message),
  });
  const renameMutation = useMutation({
    mutationFn: ({ id, n }: { id: string; n: string }) =>
      dashboardApi.updateCategory(id, { name: n }),
    onSuccess: () => {
      setEditingId(null);
      onChanged();
    },
    onError: (e: Error) => onError(e.message),
  });
  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      dashboardApi.updateCategory(id, { isActive: active }),
    onSuccess: onChanged,
    onError: (e: Error) => onError(e.message),
  });
  const reorderMutation = useMutation({
    mutationFn: ({ id, sortOrder }: { id: string; sortOrder: number }) =>
      dashboardApi.updateCategory(id, { sortOrder }),
    onSuccess: onChanged,
    onError: (e: Error) => onError(e.message),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => dashboardApi.deleteCategory(id),
    onSuccess: onChanged,
    onError: (e: Error) => onError(e.message),
  });

  const countFor = (categoryId: string) =>
    items.filter((d) => d.categoryId === categoryId).length;

  return (
    <aside className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="eyebrow">Categories</h2>
      </div>

      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          onError(null);
          if (name.trim()) createMutation.mutate(name.trim());
        }}
        className="flex gap-2"
      >
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New category"
          className="w-full min-w-0 rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus-visible:border-ring"
        />
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="shrink-0 rounded-full bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-60"
        >
          Add
        </button>
      </form>

      <ul className="space-y-1">
        <li>
          <button
            type="button"
            onClick={() => onSelect("all")}
            className={`w-full rounded-lg px-3 py-2 text-left text-sm font-semibold ${
              selectedId === "all"
                ? "bg-surface-strong text-background"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            }`}
          >
            All dishes ({items.length})
          </button>
        </li>

        {categories.map((c) => (
          <li key={c.id} className="rounded-lg border border-border bg-card">
            {editingId === c.id ? (
              <div className="flex items-center gap-2 p-2">
                <input
                  value={editingName}
                  onChange={(e) => setEditingName(e.target.value)}
                  className="w-full min-w-0 rounded-lg border border-border bg-background px-2 py-1.5 text-sm outline-none focus-visible:border-ring"
                />
                <button
                  type="button"
                  onClick={() =>
                    renameMutation.mutate({ id: c.id, n: editingName.trim() })
                  }
                  className="shrink-0 rounded-full bg-primary px-2.5 py-1 text-xs font-semibold text-primary-foreground"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setEditingId(null)}
                  className="shrink-0 rounded-full border border-border px-2.5 py-1 text-xs font-semibold"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <div className="p-2">
                <button
                  type="button"
                  onClick={() => onSelect(c.id)}
                  className={`flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm font-semibold ${
                    selectedId === c.id ? "bg-secondary" : ""
                  }`}
                >
                  <span
                    className={
                      c.isActive === false
                        ? "text-muted-foreground line-through"
                        : ""
                    }
                  >
                    {c.name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {countFor(c.id)}
                  </span>
                </button>
                <div className="mt-1 flex flex-wrap items-center gap-1">
                  <button
                    type="button"
                    aria-label="Move up"
                    onClick={() =>
                      reorderMutation.mutate({
                        id: c.id,
                        sortOrder: c.sortOrder - 1,
                      })
                    }
                    className="rounded p-1 text-muted-foreground hover:bg-secondary"
                  >
                    <ChevronUp aria-hidden className="size-4" />
                  </button>
                  <button
                    type="button"
                    aria-label="Move down"
                    onClick={() =>
                      reorderMutation.mutate({
                        id: c.id,
                        sortOrder: c.sortOrder + 1,
                      })
                    }
                    className="rounded p-1 text-muted-foreground hover:bg-secondary"
                  >
                    <ChevronDown aria-hidden className="size-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      toggleMutation.mutate({
                        id: c.id,
                        active: c.isActive === false,
                      })
                    }
                    className="rounded-full border border-border px-2 py-0.5 text-xs font-semibold hover:bg-secondary"
                  >
                    {c.isActive === false ? "Enable" : "Disable"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEditingId(c.id);
                      setEditingName(c.name);
                    }}
                    className="rounded-full border border-border px-2 py-0.5 text-xs font-semibold hover:bg-secondary"
                  >
                    Rename
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate(c.id)}
                    className="rounded-full border border-border px-2 py-0.5 text-xs font-semibold text-destructive hover:bg-destructive/10"
                  >
                    Delete
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}

        {categories.length === 0 ? (
          <li className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
            No categories yet — add your first category.
          </li>
        ) : null}
      </ul>
    </aside>
  );
}

function DishPanel({
  categories,
  items,
  categoryNameById,
  onError,
  onChanged,
}: {
  categories: Category[];
  items: Dish[];
  categoryNameById: Map<string, string>;
  onError: (m: string | null) => void;
  onChanged: () => void;
}) {
  const [form, setForm] = useState<DishFormState | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => dashboardApi.deleteMenuItem(id),
    onSuccess: onChanged,
    onError: (e: Error) => onError(e.message),
  });

  const imageMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      dashboardApi.uploadMenuItemImage(id, file),
    onSuccess: onChanged,
    onError: (e: Error) => onError(e.message),
  });

  const generateMutation = useMutation({
    mutationFn: (id: string) => dashboardApi.generateMenuItem(id),
    onSuccess: onChanged,
    onError: (e: Error) => onError(e.message),
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => dashboardApi.retryGeneration(id),
    onSuccess: onChanged,
    onError: (e: Error) => onError(e.message),
  });

  return (
    <section>
      <div className="flex items-center justify-between">
        <h2 className="eyebrow">Dishes</h2>
        <button
          type="button"
          onClick={() => setForm(emptyForm(categories))}
          className="inline-flex items-center gap-1 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
        >
          <Plus aria-hidden className="size-4" /> Add Dish
        </button>
      </div>

      {form ? (
        <DishForm
          form={form}
          setForm={setForm}
          categories={categories}
          onError={onError}
          onChanged={onChanged}
        />
      ) : null}

      {items.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
          No dishes yet — add your first dish.
        </div>
      ) : (
        <ul className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <li
              key={item.id}
              className="overflow-hidden rounded-2xl border border-border bg-card"
            >
              <div className="relative aspect-[4/3] w-full bg-secondary">
                {item.imageUrl ? (
                  <img
                    src={item.imageUrl}
                    alt={item.name}
                    className="size-full object-cover"
                  />
                ) : (
                  <span className="absolute inset-0 flex flex-col items-center justify-center gap-1 text-xs text-muted-foreground">
                    <ImagePlus aria-hidden className="size-6" />
                    No image
                  </span>
                )}
                {!item.isAvailable ? (
                  <span className="absolute top-2 right-2 rounded-full bg-destructive/90 px-2 py-0.5 text-xs font-semibold text-white">
                    Unavailable
                  </span>
                ) : null}
              </div>

              <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-base font-semibold">{item.name}</h3>
                  <span className="font-display text-base font-semibold">
                    ₹{item.price}
                  </span>
                </div>
                {item.description ? (
                  <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                    {item.description}
                  </p>
                ) : null}
                <p className="mt-2 text-xs text-muted-foreground">
                  {item.categoryId
                    ? (categoryNameById.get(item.categoryId) ?? "Uncategorized")
                    : "Uncategorized"}
                </p>

                <div className="mt-2">
                  {item.modelStatus === "GENERATING" ? (
                    <span className="text-xs font-semibold text-muted-foreground">
                      Generating 3D…
                    </span>
                  ) : item.modelStatus === "READY" ? (
                    <span className="rounded-full bg-veg/10 px-2 py-0.5 text-xs font-semibold text-veg">
                      3D Ready
                    </span>
                  ) : item.modelStatus === "FAILED" ? (
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-semibold text-destructive">
                        Generation failed
                      </span>
                      <button
                        type="button"
                        onClick={() => retryMutation.mutate(item.id)}
                        disabled={retryMutation.isPending}
                        className="rounded-full border border-border px-2 py-0.5 text-xs font-semibold hover:bg-secondary"
                      >
                        Retry
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => generateMutation.mutate(item.id)}
                      disabled={generateMutation.isPending}
                      className="rounded-full border border-border px-3 py-1 text-xs font-semibold hover:bg-secondary"
                    >
                      Generate 3D
                    </button>
                  )}
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setForm(formFromDish(item))}
                    className="rounded-full border border-border px-3 py-1.5 text-xs font-semibold hover:bg-secondary"
                  >
                    Edit
                  </button>
                  <label className="cursor-pointer rounded-full border border-border px-3 py-1.5 text-xs font-semibold hover:bg-secondary">
                    {imageMutation.isPending ? "Uploading…" : "Change image"}
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) imageMutation.mutate({ id: item.id, file });
                      }}
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate(item.id)}
                    className="rounded-full border border-border px-3 py-1.5 text-xs font-semibold text-destructive hover:bg-destructive/10"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function DishForm({
  form,
  setForm,
  categories,
  onError,
  onChanged,
}: {
  form: DishFormState;
  setForm: (f: DishFormState | null) => void;
  categories: Category[];
  onError: (m: string | null) => void;
  onChanged: () => void;
}) {
  const [saving, setSaving] = useState(false);

  const update = (patch: Partial<DishFormState>) =>
    setForm({ ...form, ...patch });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    onError(null);
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const fields = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        price: Number(form.price) || 0,
        category_id: form.categoryId || null,
        is_available: form.isAvailable,
      };
      if (form.mode === "edit" && form.dish?.id) {
        await dashboardApi.updateMenuItem(form.dish.id, fields);
        if (form.imageFile)
          await dashboardApi.uploadMenuItemImage(form.dish.id, form.imageFile);
      } else {
        const created = await dashboardApi.createMenuItem(fields);
        if (form.imageFile)
          await dashboardApi.uploadMenuItemImage(created.id, form.imageFile);
      }
      setForm(null);
      await onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to save dish");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="mt-4 space-y-4 rounded-2xl border border-border bg-card p-4"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">
          {form.mode === "add" ? "Add dish" : "Edit dish"}
        </h3>
        <button
          type="button"
          onClick={() => setForm(null)}
          aria-label="Close"
          className="rounded-full p-1 text-muted-foreground hover:bg-secondary"
        >
          <X aria-hidden className="size-5" />
        </button>
      </div>

      {form.mode === "edit" && form.dish?.imageUrl ? (
        <img
          src={form.dish.imageUrl}
          alt={form.dish.name}
          className="h-28 w-full rounded-xl object-cover"
        />
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="text-sm font-semibold">Name</label>
          <input
            value={form.name}
            onChange={(e) => update({ name: e.target.value })}
            required
            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring"
          />
        </div>
        <div>
          <label className="text-sm font-semibold">Price (₹)</label>
          <input
            type="number"
            min="0"
            value={form.price}
            onChange={(e) => update({ price: e.target.value })}
            required
            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring"
          />
        </div>
      </div>

      <div>
        <label className="text-sm font-semibold">Description</label>
        <textarea
          value={form.description}
          onChange={(e) => update({ description: e.target.value })}
          rows={3}
          className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="text-sm font-semibold">Category</label>
          <select
            value={form.categoryId}
            onChange={(e) => update({ categoryId: e.target.value })}
            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:border-ring"
          >
            <option value="">No category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 text-sm font-semibold">
            <input
              type="checkbox"
              checked={form.isAvailable}
              onChange={(e) => update({ isAvailable: e.target.checked })}
            />
            Available
          </label>
        </div>
      </div>

      <div>
        <label className="text-sm font-semibold">
          Dish image {form.mode === "add" ? "(required)" : "(optional)"}
        </label>
        <input
          type="file"
          accept="image/*"
          required={form.mode === "add" && !form.dish?.imageUrl}
          onChange={(e) => update({ imageFile: e.target.files?.[0] ?? null })}
          className="mt-1 block w-full text-sm text-muted-foreground file:mr-3 file:rounded-full file:border-0 file:bg-primary file:px-4 file:py-1.5 file:text-sm file:font-semibold file:text-primary-foreground"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-60"
        >
          {saving ? "Saving…" : "Save dish"}
        </button>
        <button
          type="button"
          onClick={() => setForm(null)}
          className="rounded-full border border-border px-4 py-2 text-sm font-semibold"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
