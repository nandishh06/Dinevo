-- Dscape Phase 1 — SaaS foundation schema + RLS.
--
-- Apply against a Supabase PostgreSQL database (Dashboard > SQL editor, or
-- `supabase db push` / `supabase migration up`).
--
-- Tenant model:
--   auth.users  ->  profiles (1:1)  ->  restaurants (owner_id)  ->  categories
--                                                                 ->  menu_items
--
-- Security model:
--   - RLS is owner-only on all SaaS tables. There is NO public read policy:
--     customer menus are served through the trusted backend (service role),
--     which scopes by restaurant slug.
--   - The service-role key bypasses RLS and lives ONLY on the server. The anon
--     key is used by the browser for Supabase Auth and is public by design.
--   - Storage bucket `restaurant-assets` is public-read (guests see food
--     photos) but writes go through the backend service role, never the client.

-- ---------------------------------------------------------------------------
-- updated_at trigger helper
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- profiles (1:1 with auth.users)
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Auto-create a profile row on signup.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, full_name)
  values (new.id, new.raw_user_meta_data ->> 'full_name')
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- restaurants
-- ---------------------------------------------------------------------------
create table if not exists public.restaurants (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.profiles (id) on delete cascade,
  slug text not null unique,
  name text not null,
  logo_url text,
  description text,
  address text,
  phone text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists restaurants_owner_id_idx on public.restaurants (owner_id);
create index if not exists restaurants_slug_idx on public.restaurants (slug);

drop trigger if exists restaurants_set_updated_at on public.restaurants;
create trigger restaurants_set_updated_at
  before update on public.restaurants
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- categories
-- ---------------------------------------------------------------------------
create table if not exists public.categories (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references public.restaurants (id) on delete cascade,
  name text not null,
  sort_order integer not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists categories_restaurant_id_idx on public.categories (restaurant_id);

drop trigger if exists categories_set_updated_at on public.categories;
create trigger categories_set_updated_at
  before update on public.categories
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- menu_items
-- ---------------------------------------------------------------------------
create table if not exists public.menu_items (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references public.restaurants (id) on delete cascade,
  category_id uuid references public.categories (id) on delete set null,
  name text not null,
  description text,
  -- Whole minor-unit-free rupees, matching the existing frontend Dish model.
  price integer not null default 0,
  image_url text,
  is_available boolean not null default true,
  is_featured boolean not null default false,
  -- Backend-ready fields for the future paid 3D/AR system. NOT populated or
  -- driven by the dashboard yet; they exist so the data model can support AR.
  model_url text,
  model_status text,
  dietary text check (dietary in ('VEG', 'NON_VEG', 'EGG')),
  ingredients text[] not null default '{}',
  spice_level integer check (spice_level between 0 and 3),
  calories integer,
  tags text[] not null default '{}',
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists menu_items_restaurant_id_idx on public.menu_items (restaurant_id);
create index if not exists menu_items_category_id_idx on public.menu_items (category_id);

drop trigger if exists menu_items_set_updated_at on public.menu_items;
create trigger menu_items_set_updated_at
  before update on public.menu_items
  for each row execute function public.set_updated_at();

-- ===========================================================================
-- ROW LEVEL SECURITY
-- ===========================================================================
-- All SaaS tables are owner-only. No public read: the customer menu is served
-- by the trusted backend (service role) scoped by slug, so a direct anon query
-- cannot read any restaurant/menu data.

alter table public.profiles enable row level security;
alter table public.restaurants enable row level security;
alter table public.categories enable row level security;
alter table public.menu_items enable row level security;

-- profiles ---------------------------------------------------------------
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles
  for select using (auth.uid() = id);

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own" on public.profiles
  for insert with check (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles
  for update using (auth.uid() = id);

-- restaurants -------------------------------------------------------------
drop policy if exists "restaurants_select_own" on public.restaurants;
create policy "restaurants_select_own" on public.restaurants
  for select using (auth.uid() = owner_id);

drop policy if exists "restaurants_insert_own" on public.restaurants;
create policy "restaurants_insert_own" on public.restaurants
  for insert with check (auth.uid() = owner_id);

drop policy if exists "restaurants_update_own" on public.restaurants;
create policy "restaurants_update_own" on public.restaurants
  for update using (auth.uid() = owner_id);

drop policy if exists "restaurants_delete_own" on public.restaurants;
create policy "restaurants_delete_own" on public.restaurants
  for delete using (auth.uid() = owner_id);

-- categories --------------------------------------------------------------
drop policy if exists "categories_select_own" on public.categories;
create policy "categories_select_own" on public.categories
  for select using (
    exists (select 1 from public.restaurants r where r.id = restaurant_id and r.owner_id = auth.uid())
  );

drop policy if exists "categories_insert_own" on public.categories;
create policy "categories_insert_own" on public.categories
  for insert with check (
    exists (select 1 from public.restaurants r where r.id = restaurant_id and r.owner_id = auth.uid())
  );

drop policy if exists "categories_update_own" on public.categories;
create policy "categories_update_own" on public.categories
  for update using (
    exists (select 1 from public.restaurants r where r.id = restaurant_id and r.owner_id = auth.uid())
  );

drop policy if exists "categories_delete_own" on public.categories;
create policy "categories_delete_own" on public.categories
  for delete using (
    exists (select 1 from public.restaurants r where r.id = restaurant_id and r.owner_id = auth.uid())
  );

-- menu_items --------------------------------------------------------------
drop policy if exists "menu_items_select_own" on public.menu_items;
create policy "menu_items_select_own" on public.menu_items
  for select using (
    exists (select 1 from public.restaurants r where r.id = restaurant_id and r.owner_id = auth.uid())
  );

drop policy if exists "menu_items_insert_own" on public.menu_items;
create policy "menu_items_insert_own" on public.menu_items
  for insert with check (
    exists (select 1 from public.restaurants r where r.id = restaurant_id and r.owner_id = auth.uid())
  );

drop policy if exists "menu_items_update_own" on public.menu_items;
create policy "menu_items_update_own" on public.menu_items
  for update using (
    exists (select 1 from public.restaurants r where r.id = restaurant_id and r.owner_id = auth.uid())
  );

drop policy if exists "menu_items_delete_own" on public.menu_items;
create policy "menu_items_delete_own" on public.menu_items
  for delete using (
    exists (select 1 from public.restaurants r where r.id = restaurant_id and r.owner_id = auth.uid())
  );

-- ===========================================================================
-- STORAGE — public read, service-role write
-- ===========================================================================
-- Bucket is created below; it must be PUBLIC so guests can load food photos.
-- Writes are done by the backend using the service-role key (which bypasses
-- RLS). Anon/authenticated users get read-only access to object SELECT via the
-- public bucket; they are never granted object write policies.

insert into storage.buckets (id, name, public)
values ('restaurant-assets', 'restaurant-assets', true)
on conflict (id) do update set public = true;

drop policy if exists "restaurant_assets_public_read" on storage.objects;
create policy "restaurant_assets_public_read" on storage.objects
  for select using (bucket_id = 'restaurant-assets');
