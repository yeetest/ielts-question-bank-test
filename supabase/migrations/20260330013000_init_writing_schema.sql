create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  credits integer not null default 0 check (credits >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.credit_transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  delta integer not null,
  balance_after integer,
  source text not null,
  description text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.writing_tasks (
  id text primary key,
  task_type text not null check (task_type in ('task1', 'task2')),
  title text not null,
  prompt text not null,
  source text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.practice_records (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  task_id text not null,
  task_type text not null check (task_type in ('task1', 'task2')),
  task_title text not null,
  task_prompt text not null,
  original_essay text not null default '',
  correction_result jsonb,
  is_saved boolean not null default false,
  saved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, task_id)
);

create table if not exists public.highlights (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  practice_record_id uuid not null references public.practice_records(id) on delete cascade,
  source text not null default 'revised',
  text_en text not null,
  text_zh text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (practice_record_id, text_en)
);

create table if not exists public.flashcards (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  practice_record_id uuid not null references public.practice_records(id) on delete cascade,
  highlight_id uuid not null unique references public.highlights(id) on delete cascade,
  front_zh text not null,
  back_en text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.pending_actions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  action_type text not null,
  task_id text,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'pending' check (status in ('pending', 'completed', 'cancelled', 'failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, coalesce(lower(new.email), ''))
  on conflict (id) do update
    set email = excluded.email,
        updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert or update of email on auth.users
for each row
execute function public.handle_new_user();

create or replace function public.sync_flashcard_from_highlight()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.flashcards (
    user_id,
    practice_record_id,
    highlight_id,
    front_zh,
    back_en
  )
  values (
    new.user_id,
    new.practice_record_id,
    new.id,
    new.text_zh,
    new.text_en
  )
  on conflict (highlight_id) do update
    set front_zh = excluded.front_zh,
        back_en = excluded.back_en,
        updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_highlight_sync_flashcard on public.highlights;
create trigger on_highlight_sync_flashcard
after insert or update on public.highlights
for each row
execute function public.sync_flashcard_from_highlight();

drop trigger if exists set_profiles_updated_at on public.profiles;
create trigger set_profiles_updated_at
before update on public.profiles
for each row
execute function public.set_updated_at();

drop trigger if exists set_writing_tasks_updated_at on public.writing_tasks;
create trigger set_writing_tasks_updated_at
before update on public.writing_tasks
for each row
execute function public.set_updated_at();

drop trigger if exists set_practice_records_updated_at on public.practice_records;
create trigger set_practice_records_updated_at
before update on public.practice_records
for each row
execute function public.set_updated_at();

drop trigger if exists set_highlights_updated_at on public.highlights;
create trigger set_highlights_updated_at
before update on public.highlights
for each row
execute function public.set_updated_at();

drop trigger if exists set_flashcards_updated_at on public.flashcards;
create trigger set_flashcards_updated_at
before update on public.flashcards
for each row
execute function public.set_updated_at();

drop trigger if exists set_pending_actions_updated_at on public.pending_actions;
create trigger set_pending_actions_updated_at
before update on public.pending_actions
for each row
execute function public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.credit_transactions enable row level security;
alter table public.writing_tasks enable row level security;
alter table public.practice_records enable row level security;
alter table public.highlights enable row level security;
alter table public.flashcards enable row level security;
alter table public.pending_actions enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
on public.profiles
for select
using (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
on public.profiles
for update
using (auth.uid() = id)
with check (auth.uid() = id);

drop policy if exists "credit_transactions_select_own" on public.credit_transactions;
create policy "credit_transactions_select_own"
on public.credit_transactions
for select
using (auth.uid() = user_id);

drop policy if exists "writing_tasks_read_all" on public.writing_tasks;
create policy "writing_tasks_read_all"
on public.writing_tasks
for select
using (true);

drop policy if exists "practice_records_select_own" on public.practice_records;
create policy "practice_records_select_own"
on public.practice_records
for select
using (auth.uid() = user_id);

drop policy if exists "practice_records_insert_own" on public.practice_records;
create policy "practice_records_insert_own"
on public.practice_records
for insert
with check (auth.uid() = user_id);

drop policy if exists "practice_records_update_own" on public.practice_records;
create policy "practice_records_update_own"
on public.practice_records
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "practice_records_delete_own" on public.practice_records;
create policy "practice_records_delete_own"
on public.practice_records
for delete
using (auth.uid() = user_id);

drop policy if exists "highlights_select_own" on public.highlights;
create policy "highlights_select_own"
on public.highlights
for select
using (auth.uid() = user_id);

drop policy if exists "highlights_insert_own" on public.highlights;
create policy "highlights_insert_own"
on public.highlights
for insert
with check (auth.uid() = user_id);

drop policy if exists "highlights_update_own" on public.highlights;
create policy "highlights_update_own"
on public.highlights
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "highlights_delete_own" on public.highlights;
create policy "highlights_delete_own"
on public.highlights
for delete
using (auth.uid() = user_id);

drop policy if exists "flashcards_select_own" on public.flashcards;
create policy "flashcards_select_own"
on public.flashcards
for select
using (auth.uid() = user_id);

drop policy if exists "pending_actions_select_own" on public.pending_actions;
create policy "pending_actions_select_own"
on public.pending_actions
for select
using (auth.uid() = user_id);

drop policy if exists "pending_actions_insert_own" on public.pending_actions;
create policy "pending_actions_insert_own"
on public.pending_actions
for insert
with check (auth.uid() = user_id);

drop policy if exists "pending_actions_update_own" on public.pending_actions;
create policy "pending_actions_update_own"
on public.pending_actions
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

insert into public.profiles (id, email)
select id, lower(email)
from auth.users
where email is not null
on conflict (id) do update
  set email = excluded.email,
      updated_at = now();
