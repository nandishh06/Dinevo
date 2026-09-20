-- Dscape — 3D generation infrastructure.
--
-- A `generations` row is one image->3D attempt for a SaaS menu item. It is
-- kept SEPARATE from `menu_items` so retries create a new row instead of
-- corrupting a previous result. `menu_items.model_url` / `model_status` are the
-- denormalized "current published model" fields the customer menu reads.

-- ---------------------------------------------------------------------------
-- generations
-- ---------------------------------------------------------------------------
create table if not exists public.generations (
  id uuid primary key default gen_random_uuid(),
  menu_item_id uuid not null references public.menu_items (id) on delete cascade,
  provider text not null,
  provider_task_id text,
  status text not null default 'QUEUED'
    check (status in ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')),
  glb_url text,
  usdz_url text,
  preview_urls text,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists generations_menu_item_id_idx on public.generations (menu_item_id);

drop trigger if exists generations_set_updated_at on public.generations;
create trigger generations_set_updated_at
  before update on public.generations
  for each row execute function public.set_updated_at();

-- ===========================================================================
-- ROW LEVEL SECURITY
-- ===========================================================================
-- Owner-only through the chain generation -> menu_item -> restaurant -> owner_id.
-- No public read: the customer menu reads only menu_items.model_url, never the
-- generations table.

alter table public.generations enable row level security;

drop policy if exists "generations_select_own" on public.generations;
create policy "generations_select_own" on public.generations
  for select using (
    exists (
      select 1
      from public.menu_items mi
      join public.restaurants r on r.id = mi.restaurant_id
      where mi.id = menu_item_id and r.owner_id = auth.uid()
    )
  );

drop policy if exists "generations_insert_own" on public.generations;
create policy "generations_insert_own" on public.generations
  for insert with check (
    exists (
      select 1
      from public.menu_items mi
      join public.restaurants r on r.id = mi.restaurant_id
      where mi.id = menu_item_id and r.owner_id = auth.uid()
    )
  );

drop policy if exists "generations_update_own" on public.generations;
create policy "generations_update_own" on public.generations
  for update using (
    exists (
      select 1
      from public.menu_items mi
      join public.restaurants r on r.id = mi.restaurant_id
      where mi.id = menu_item_id and r.owner_id = auth.uid()
    )
  );

drop policy if exists "generations_delete_own" on public.generations;
create policy "generations_delete_own" on public.generations
  for delete using (
    exists (
      select 1
      from public.menu_items mi
      join public.restaurants r on r.id = mi.restaurant_id
      where mi.id = menu_item_id and r.owner_id = auth.uid()
    )
  );

-- ===========================================================================
-- STORAGE — generated models (public read, service-role write)
-- ===========================================================================
insert into storage.buckets (id, name, public)
values ('restaurant-models', 'restaurant-models', true)
on conflict (id) do update set public = true;

drop policy if exists "restaurant_models_public_read" on storage.objects;
create policy "restaurant_models_public_read" on storage.objects
  for select using (bucket_id = 'restaurant-models');
