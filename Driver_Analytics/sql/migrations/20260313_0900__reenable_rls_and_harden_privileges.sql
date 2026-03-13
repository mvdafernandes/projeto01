begin;

-- Security hardening for multi-tenant access.
-- The Python backend may use the Supabase service key; service_role keeps backend access.
-- RLS and grants below protect direct database/API access by anon/authenticated roles.

-- Helper used by ownership policies. It reads the custom user_id claim when present.
create or replace function public.app_current_user_id()
returns bigint
language plpgsql
stable
as $$
declare
  raw_claims text;
  claims jsonb;
  direct_user_id text;
  meta_user_id text;
  metadata_user_id text;
begin
  raw_claims := nullif(current_setting('request.jwt.claims', true), '');
  if raw_claims is null then
    return null;
  end if;

  claims := raw_claims::jsonb;
  direct_user_id := nullif(claims ->> 'user_id', '');
  meta_user_id := nullif(claims -> 'app_metadata' ->> 'user_id', '');
  metadata_user_id := nullif(claims -> 'user_metadata' ->> 'user_id', '');

  return coalesce(direct_user_id, meta_user_id, metadata_user_id)::bigint;
exception
  when others then
    return null;
end;
$$;

comment on function public.app_current_user_id()
  is 'Returns the application-level user_id from JWT claims when available.';

grant execute on function public.app_current_user_id() to anon, authenticated, service_role;

-- Lock down schema usage for direct clients. service_role keeps full backend access.
revoke usage on schema public from anon;
grant usage on schema public to authenticated, service_role;

-- Sensitive auth tables: no direct access for anon; authenticated can only access own row/session.
alter table if exists public.usuarios enable row level security;
alter table if exists public.auth_sessions enable row level security;

revoke all on table public.usuarios from anon, authenticated;
revoke all on table public.auth_sessions from anon, authenticated;
grant select, update on table public.usuarios to authenticated;
grant select, update, delete on table public.auth_sessions to authenticated;
grant select, insert, update, delete on table public.usuarios to service_role;
grant select, insert, update, delete on table public.auth_sessions to service_role;
revoke all on sequence public.usuarios_id_seq from anon, authenticated;
grant usage, select on sequence public.usuarios_id_seq to service_role;

drop policy if exists usuarios_self_select on public.usuarios;
drop policy if exists usuarios_self_update on public.usuarios;
create policy usuarios_self_select
  on public.usuarios
  for select
  to authenticated
  using (id = public.app_current_user_id());
create policy usuarios_self_update
  on public.usuarios
  for update
  to authenticated
  using (id = public.app_current_user_id())
  with check (id = public.app_current_user_id());

drop policy if exists auth_sessions_self_select on public.auth_sessions;
drop policy if exists auth_sessions_self_update on public.auth_sessions;
drop policy if exists auth_sessions_self_delete on public.auth_sessions;
create policy auth_sessions_self_select
  on public.auth_sessions
  for select
  to authenticated
  using (user_id = public.app_current_user_id());
create policy auth_sessions_self_update
  on public.auth_sessions
  for update
  to authenticated
  using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());
create policy auth_sessions_self_delete
  on public.auth_sessions
  for delete
  to authenticated
  using (user_id = public.app_current_user_id());

-- User-owned business tables: authenticated role may access only rows whose user_id matches the JWT claim.
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'receitas') then
    alter table public.receitas enable row level security;
    revoke all on table public.receitas from anon;
    grant select, insert, update, delete on table public.receitas to authenticated, service_role;
    if exists (select 1 from pg_class where relname = 'receitas_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.receitas_id_seq from anon;
      grant usage, select on sequence public.receitas_id_seq to authenticated, service_role;
    end if;

    drop policy if exists receitas_owner_select on public.receitas;
    drop policy if exists receitas_owner_insert on public.receitas;
    drop policy if exists receitas_owner_update on public.receitas;
    drop policy if exists receitas_owner_delete on public.receitas;
    create policy receitas_owner_select on public.receitas
      for select to authenticated
      using (user_id = public.app_current_user_id());
    create policy receitas_owner_insert on public.receitas
      for insert to authenticated
      with check (user_id = public.app_current_user_id());
    create policy receitas_owner_update on public.receitas
      for update to authenticated
      using (user_id = public.app_current_user_id())
      with check (user_id = public.app_current_user_id());
    create policy receitas_owner_delete on public.receitas
      for delete to authenticated
      using (user_id = public.app_current_user_id());
  end if;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'despesas') then
    alter table public.despesas enable row level security;
    revoke all on table public.despesas from anon;
    grant select, insert, update, delete on table public.despesas to authenticated, service_role;
    if exists (select 1 from pg_class where relname = 'despesas_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.despesas_id_seq from anon;
      grant usage, select on sequence public.despesas_id_seq to authenticated, service_role;
    end if;

    drop policy if exists despesas_owner_select on public.despesas;
    drop policy if exists despesas_owner_insert on public.despesas;
    drop policy if exists despesas_owner_update on public.despesas;
    drop policy if exists despesas_owner_delete on public.despesas;
    create policy despesas_owner_select on public.despesas
      for select to authenticated
      using (user_id = public.app_current_user_id());
    create policy despesas_owner_insert on public.despesas
      for insert to authenticated
      with check (user_id = public.app_current_user_id());
    create policy despesas_owner_update on public.despesas
      for update to authenticated
      using (user_id = public.app_current_user_id())
      with check (user_id = public.app_current_user_id());
    create policy despesas_owner_delete on public.despesas
      for delete to authenticated
      using (user_id = public.app_current_user_id());
  end if;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'investimentos') then
    alter table public.investimentos enable row level security;
    revoke all on table public.investimentos from anon;
    grant select, insert, update, delete on table public.investimentos to authenticated, service_role;
    if exists (select 1 from pg_class where relname = 'investimentos_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.investimentos_id_seq from anon;
      grant usage, select on sequence public.investimentos_id_seq to authenticated, service_role;
    end if;

    drop policy if exists investimentos_owner_select on public.investimentos;
    drop policy if exists investimentos_owner_insert on public.investimentos;
    drop policy if exists investimentos_owner_update on public.investimentos;
    drop policy if exists investimentos_owner_delete on public.investimentos;
    create policy investimentos_owner_select on public.investimentos
      for select to authenticated
      using (user_id = public.app_current_user_id());
    create policy investimentos_owner_insert on public.investimentos
      for insert to authenticated
      with check (user_id = public.app_current_user_id());
    create policy investimentos_owner_update on public.investimentos
      for update to authenticated
      using (user_id = public.app_current_user_id())
      with check (user_id = public.app_current_user_id());
    create policy investimentos_owner_delete on public.investimentos
      for delete to authenticated
      using (user_id = public.app_current_user_id());
  end if;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'categorias_despesas') then
    alter table public.categorias_despesas enable row level security;
    revoke all on table public.categorias_despesas from anon;
    grant select, insert, update, delete on table public.categorias_despesas to authenticated, service_role;
    if exists (select 1 from pg_class where relname = 'categorias_despesas_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.categorias_despesas_id_seq from anon;
      grant usage, select on sequence public.categorias_despesas_id_seq to authenticated, service_role;
    end if;

    drop policy if exists categorias_owner_select on public.categorias_despesas;
    drop policy if exists categorias_owner_insert on public.categorias_despesas;
    drop policy if exists categorias_owner_update on public.categorias_despesas;
    drop policy if exists categorias_owner_delete on public.categorias_despesas;
    create policy categorias_owner_select on public.categorias_despesas
      for select to authenticated
      using (user_id = public.app_current_user_id());
    create policy categorias_owner_insert on public.categorias_despesas
      for insert to authenticated
      with check (user_id = public.app_current_user_id());
    create policy categorias_owner_update on public.categorias_despesas
      for update to authenticated
      using (user_id = public.app_current_user_id())
      with check (user_id = public.app_current_user_id());
    create policy categorias_owner_delete on public.categorias_despesas
      for delete to authenticated
      using (user_id = public.app_current_user_id());
  end if;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_km') then
    alter table public.controle_km enable row level security;
    revoke all on table public.controle_km from anon;
    grant select, insert, update, delete on table public.controle_km to authenticated, service_role;
    if exists (select 1 from pg_class where relname = 'controle_km_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.controle_km_id_seq from anon;
      grant usage, select on sequence public.controle_km_id_seq to authenticated, service_role;
    end if;

    drop policy if exists controle_km_owner_select on public.controle_km;
    drop policy if exists controle_km_owner_insert on public.controle_km;
    drop policy if exists controle_km_owner_update on public.controle_km;
    drop policy if exists controle_km_owner_delete on public.controle_km;
    create policy controle_km_owner_select on public.controle_km
      for select to authenticated
      using (user_id = public.app_current_user_id());
    create policy controle_km_owner_insert on public.controle_km
      for insert to authenticated
      with check (user_id = public.app_current_user_id());
    create policy controle_km_owner_update on public.controle_km
      for update to authenticated
      using (user_id = public.app_current_user_id())
      with check (user_id = public.app_current_user_id());
    create policy controle_km_owner_delete on public.controle_km
      for delete to authenticated
      using (user_id = public.app_current_user_id());
  end if;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_litros') then
    alter table public.controle_litros enable row level security;
    revoke all on table public.controle_litros from anon;
    grant select, insert, update, delete on table public.controle_litros to authenticated, service_role;
    if exists (select 1 from pg_class where relname = 'controle_litros_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.controle_litros_id_seq from anon;
      grant usage, select on sequence public.controle_litros_id_seq to authenticated, service_role;
    end if;

    drop policy if exists controle_litros_owner_select on public.controle_litros;
    drop policy if exists controle_litros_owner_insert on public.controle_litros;
    drop policy if exists controle_litros_owner_update on public.controle_litros;
    drop policy if exists controle_litros_owner_delete on public.controle_litros;
    create policy controle_litros_owner_select on public.controle_litros
      for select to authenticated
      using (user_id = public.app_current_user_id());
    create policy controle_litros_owner_insert on public.controle_litros
      for insert to authenticated
      with check (user_id = public.app_current_user_id());
    create policy controle_litros_owner_update on public.controle_litros
      for update to authenticated
      using (user_id = public.app_current_user_id())
      with check (user_id = public.app_current_user_id());
    create policy controle_litros_owner_delete on public.controle_litros
      for delete to authenticated
      using (user_id = public.app_current_user_id());
  end if;
end $$;

commit;
