begin;

-- Meta diária configurável por usuário.
alter table if exists public.usuarios
  add column if not exists daily_goal numeric not null default 300;

-- Controle histórico de KM total por período fechado.
create table if not exists public.work_km_periods (
  id bigserial primary key,
  user_id bigint not null references public.usuarios(id) on delete cascade,
  start_date date not null,
  end_date date not null,
  km_total_periodo numeric not null default 0,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ck_work_km_periods_dates check (end_date >= start_date),
  constraint ck_work_km_periods_total check (km_total_periodo >= 0)
);

create index if not exists idx_work_km_periods_user_id on public.work_km_periods (user_id);
create index if not exists idx_work_km_periods_user_dates on public.work_km_periods (user_id, start_date desc, end_date desc);

create or replace function public.set_work_km_periods_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_work_km_periods_set_updated_at on public.work_km_periods;
create trigger trg_work_km_periods_set_updated_at
before update on public.work_km_periods
for each row
execute function public.set_work_km_periods_updated_at();

alter table if exists public.work_km_periods enable row level security;

revoke all on table public.work_km_periods from anon, authenticated;
grant select, insert, update, delete on table public.work_km_periods to service_role;

revoke all on sequence public.work_km_periods_id_seq from anon, authenticated;
grant usage, select on sequence public.work_km_periods_id_seq to service_role;

drop policy if exists work_km_periods_owner_select on public.work_km_periods;
drop policy if exists work_km_periods_owner_insert on public.work_km_periods;
drop policy if exists work_km_periods_owner_update on public.work_km_periods;
drop policy if exists work_km_periods_owner_delete on public.work_km_periods;

commit;
