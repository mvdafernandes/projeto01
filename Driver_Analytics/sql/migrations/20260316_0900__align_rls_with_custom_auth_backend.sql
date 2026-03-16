begin;

-- This project does not authenticate end users through Supabase Auth.
-- Application authentication is custom and enforced in Python/repositories.
-- Because of that, anon/authenticated database roles must not have direct access
-- to private tables based on JWT claims that do not exist in this architecture.
-- The backend may use the service_role key, which bypasses RLS by design.

-- Remove claim-based helper introduced by previous hardening attempts.
drop function if exists public.app_current_user_id();

-- Direct client roles should not use the private application schema.
revoke usage on schema public from anon, authenticated;
grant usage on schema public to service_role;

-- Private auth tables remain under RLS, but only service_role is allowed.
alter table if exists public.usuarios enable row level security;
alter table if exists public.auth_sessions enable row level security;

revoke all on table public.usuarios from anon, authenticated;
revoke all on table public.auth_sessions from anon, authenticated;
grant select, insert, update, delete on table public.usuarios to service_role;
grant select, insert, update, delete on table public.auth_sessions to service_role;

revoke all on sequence public.usuarios_id_seq from anon, authenticated;
grant usage, select on sequence public.usuarios_id_seq to service_role;

drop policy if exists usuarios_self_select on public.usuarios;
drop policy if exists usuarios_self_update on public.usuarios;
drop policy if exists auth_sessions_self_select on public.auth_sessions;
drop policy if exists auth_sessions_self_update on public.auth_sessions;
drop policy if exists auth_sessions_self_delete on public.auth_sessions;

-- Business tables are private to the backend. RLS stays enabled to keep the
-- default posture restrictive for non-service roles, even though service_role bypasses it.
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'receitas') then
    alter table public.receitas enable row level security;
    revoke all on table public.receitas from anon, authenticated;
    grant select, insert, update, delete on table public.receitas to service_role;
    if exists (select 1 from pg_class where relname = 'receitas_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.receitas_id_seq from anon, authenticated;
      grant usage, select on sequence public.receitas_id_seq to service_role;
    end if;
    drop policy if exists receitas_owner_select on public.receitas;
    drop policy if exists receitas_owner_insert on public.receitas;
    drop policy if exists receitas_owner_update on public.receitas;
    drop policy if exists receitas_owner_delete on public.receitas;
  end if;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'despesas') then
    alter table public.despesas enable row level security;
    revoke all on table public.despesas from anon, authenticated;
    grant select, insert, update, delete on table public.despesas to service_role;
    if exists (select 1 from pg_class where relname = 'despesas_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.despesas_id_seq from anon, authenticated;
      grant usage, select on sequence public.despesas_id_seq to service_role;
    end if;
    drop policy if exists despesas_owner_select on public.despesas;
    drop policy if exists despesas_owner_insert on public.despesas;
    drop policy if exists despesas_owner_update on public.despesas;
    drop policy if exists despesas_owner_delete on public.despesas;
  end if;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'investimentos') then
    alter table public.investimentos enable row level security;
    revoke all on table public.investimentos from anon, authenticated;
    grant select, insert, update, delete on table public.investimentos to service_role;
    if exists (select 1 from pg_class where relname = 'investimentos_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.investimentos_id_seq from anon, authenticated;
      grant usage, select on sequence public.investimentos_id_seq to service_role;
    end if;
    drop policy if exists investimentos_owner_select on public.investimentos;
    drop policy if exists investimentos_owner_insert on public.investimentos;
    drop policy if exists investimentos_owner_update on public.investimentos;
    drop policy if exists investimentos_owner_delete on public.investimentos;
  end if;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'categorias_despesas') then
    alter table public.categorias_despesas enable row level security;
    revoke all on table public.categorias_despesas from anon, authenticated;
    grant select, insert, update, delete on table public.categorias_despesas to service_role;
    if exists (select 1 from pg_class where relname = 'categorias_despesas_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.categorias_despesas_id_seq from anon, authenticated;
      grant usage, select on sequence public.categorias_despesas_id_seq to service_role;
    end if;
    drop policy if exists categorias_owner_select on public.categorias_despesas;
    drop policy if exists categorias_owner_insert on public.categorias_despesas;
    drop policy if exists categorias_owner_update on public.categorias_despesas;
    drop policy if exists categorias_owner_delete on public.categorias_despesas;
  end if;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_km') then
    alter table public.controle_km enable row level security;
    revoke all on table public.controle_km from anon, authenticated;
    grant select, insert, update, delete on table public.controle_km to service_role;
    if exists (select 1 from pg_class where relname = 'controle_km_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.controle_km_id_seq from anon, authenticated;
      grant usage, select on sequence public.controle_km_id_seq to service_role;
    end if;
    drop policy if exists controle_km_owner_select on public.controle_km;
    drop policy if exists controle_km_owner_insert on public.controle_km;
    drop policy if exists controle_km_owner_update on public.controle_km;
    drop policy if exists controle_km_owner_delete on public.controle_km;
  end if;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_litros') then
    alter table public.controle_litros enable row level security;
    revoke all on table public.controle_litros from anon, authenticated;
    grant select, insert, update, delete on table public.controle_litros to service_role;
    if exists (select 1 from pg_class where relname = 'controle_litros_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.controle_litros_id_seq from anon, authenticated;
      grant usage, select on sequence public.controle_litros_id_seq to service_role;
    end if;
    drop policy if exists controle_litros_owner_select on public.controle_litros;
    drop policy if exists controle_litros_owner_insert on public.controle_litros;
    drop policy if exists controle_litros_owner_update on public.controle_litros;
    drop policy if exists controle_litros_owner_delete on public.controle_litros;
  end if;
end $$;

commit;
