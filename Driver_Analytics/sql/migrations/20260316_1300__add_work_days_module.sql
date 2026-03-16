begin;

-- Jornada principal do motorista com ownership por user_id.
create table if not exists public.work_days (
  id bigserial primary key,
  user_id bigint not null references public.usuarios(id) on delete cascade,
  work_date date not null,
  start_time timestamptz,
  end_time timestamptz,
  start_time_source text not null default 'auto',
  end_time_source text not null default 'auto',
  start_km numeric,
  end_km numeric,
  km_remunerado numeric,
  km_nao_remunerado_antes numeric,
  worked_minutes_calculated integer,
  worked_minutes_manual integer,
  worked_minutes_final integer,
  status text not null default 'partial',
  is_manually_adjusted boolean not null default false,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ck_work_days_status check (status in ('open', 'closed', 'partial', 'adjusted', 'manual')),
  constraint ck_work_days_start_source check (start_time_source in ('auto', 'manual')),
  constraint ck_work_days_end_source check (end_time_source in ('auto', 'manual'))
);

create table if not exists public.work_day_events (
  id bigserial primary key,
  work_day_id bigint not null references public.work_days(id) on delete cascade,
  event_type text not null,
  event_timestamp timestamptz not null default now(),
  km_value numeric,
  old_value jsonb,
  new_value jsonb,
  notes text,
  created_at timestamptz not null default now(),
  constraint ck_work_day_events_type check (event_type in ('check_in', 'check_out', 'manual_create', 'manual_edit', 'manual_complete'))
);

create index if not exists idx_work_days_user_id on public.work_days (user_id);
create index if not exists idx_work_days_user_id_work_date on public.work_days (user_id, work_date desc);
create index if not exists idx_work_days_user_id_status on public.work_days (user_id, status);
create index if not exists idx_work_days_user_id_start_time on public.work_days (user_id, start_time desc);
create index if not exists idx_work_day_events_work_day_id on public.work_day_events (work_day_id);
create index if not exists idx_work_day_events_work_day_id_event_timestamp on public.work_day_events (work_day_id, event_timestamp desc);

create or replace function public.set_work_days_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_work_days_set_updated_at on public.work_days;
create trigger trg_work_days_set_updated_at
before update on public.work_days
for each row
execute function public.set_work_days_updated_at();

alter table if exists public.work_days enable row level security;
alter table if exists public.work_day_events enable row level security;

revoke all on table public.work_days from anon, authenticated;
revoke all on table public.work_day_events from anon, authenticated;
grant select, insert, update, delete on table public.work_days to service_role;
grant select, insert, update, delete on table public.work_day_events to service_role;

revoke all on sequence public.work_days_id_seq from anon, authenticated;
revoke all on sequence public.work_day_events_id_seq from anon, authenticated;
grant usage, select on sequence public.work_days_id_seq to service_role;
grant usage, select on sequence public.work_day_events_id_seq to service_role;

drop policy if exists work_days_owner_select on public.work_days;
drop policy if exists work_days_owner_insert on public.work_days;
drop policy if exists work_days_owner_update on public.work_days;
drop policy if exists work_days_owner_delete on public.work_days;
drop policy if exists work_day_events_owner_select on public.work_day_events;
drop policy if exists work_day_events_owner_insert on public.work_day_events;
drop policy if exists work_day_events_owner_update on public.work_day_events;
drop policy if exists work_day_events_owner_delete on public.work_day_events;

commit;
