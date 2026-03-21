begin;

create table if not exists public.auth_rate_limits (
  action text not null,
  key_hash text not null,
  failures integer not null default 0,
  blocked_until timestamptz,
  last_failure_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (action, key_hash)
);

create index if not exists idx_auth_rate_limits_blocked_until
  on public.auth_rate_limits (blocked_until);

alter table if exists public.auth_rate_limits enable row level security;

revoke all on table public.auth_rate_limits from anon, authenticated;
grant select, insert, update, delete on table public.auth_rate_limits to service_role;

drop policy if exists auth_rate_limits_backend_only on public.auth_rate_limits;
create policy auth_rate_limits_backend_only
  on public.auth_rate_limits
  as restrictive
  for all
  to public
  using (false)
  with check (false);

commit;
