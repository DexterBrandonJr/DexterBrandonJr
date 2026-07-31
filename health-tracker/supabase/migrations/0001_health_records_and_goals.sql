-- Health records and goals, scoped strictly to the owning user via RLS.
-- Every table policy below checks auth.uid() so Postgres itself refuses
-- cross-user reads/writes even if application code has a bug.

create table if not exists public.health_records (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  metric_type text not null check (char_length(metric_type) between 1 and 64),
  value numeric not null,
  unit text not null check (char_length(unit) between 1 and 16),
  recorded_at timestamptz not null default now(),
  notes text check (char_length(notes) <= 2000),
  created_at timestamptz not null default now()
);

create index if not exists health_records_user_id_recorded_at_idx
  on public.health_records (user_id, recorded_at desc);

create table if not exists public.goals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null check (char_length(title) between 1 and 200),
  metric_type text not null check (char_length(metric_type) between 1 and 64),
  target_value numeric not null,
  target_date date,
  status text not null default 'active' check (status in ('active', 'achieved', 'abandoned')),
  created_at timestamptz not null default now()
);

create index if not exists goals_user_id_idx on public.goals (user_id);

alter table public.health_records enable row level security;
alter table public.goals enable row level security;

-- Force RLS even for the table owner role (defense in depth).
alter table public.health_records force row level security;
alter table public.goals force row level security;

create policy "health_records_select_own"
  on public.health_records for select
  using (auth.uid() = user_id);

create policy "health_records_insert_own"
  on public.health_records for insert
  with check (auth.uid() = user_id);

create policy "health_records_update_own"
  on public.health_records for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "health_records_delete_own"
  on public.health_records for delete
  using (auth.uid() = user_id);

create policy "goals_select_own"
  on public.goals for select
  using (auth.uid() = user_id);

create policy "goals_insert_own"
  on public.goals for insert
  with check (auth.uid() = user_id);

create policy "goals_update_own"
  on public.goals for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "goals_delete_own"
  on public.goals for delete
  using (auth.uid() = user_id);
