begin;

-- User-owned business tables are accessed by the backend application.
-- End users do not query these tables directly with Supabase Auth JWTs.
-- Security therefore relies on three layers together:
-- 1) RLS enabled with no client-facing grants,
-- 2) schema ownership through user_id + foreign keys + indexes,
-- 3) backend repositories always filtering by user_id.

do $$
begin
  -- receitas
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'receitas') then
    if exists (select 1 from public.receitas where user_id is null) then
      raise exception 'public.receitas contains rows with user_id null. Fix ownership before applying NOT NULL.';
    end if;

    alter table public.receitas enable row level security;
    revoke all on table public.receitas from anon, authenticated;
    grant select, insert, update, delete on table public.receitas to service_role;

    if exists (select 1 from pg_class where relname = 'receitas_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.receitas_id_seq from anon, authenticated;
      grant usage, select on sequence public.receitas_id_seq to service_role;
    end if;

    alter table public.receitas alter column user_id set not null;

    if not exists (select 1 from pg_constraint where conname = 'receitas_user_id_fkey') then
      alter table public.receitas
        add constraint receitas_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;

    create index if not exists idx_receitas_user_id on public.receitas(user_id);
    create index if not exists idx_receitas_user_id_data on public.receitas(user_id, data);

    drop policy if exists receitas_owner_select on public.receitas;
    drop policy if exists receitas_owner_insert on public.receitas;
    drop policy if exists receitas_owner_update on public.receitas;
    drop policy if exists receitas_owner_delete on public.receitas;
  end if;

  -- despesas
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'despesas') then
    if exists (select 1 from public.despesas where user_id is null) then
      raise exception 'public.despesas contains rows with user_id null. Fix ownership before applying NOT NULL.';
    end if;

    alter table public.despesas enable row level security;
    revoke all on table public.despesas from anon, authenticated;
    grant select, insert, update, delete on table public.despesas to service_role;

    if exists (select 1 from pg_class where relname = 'despesas_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.despesas_id_seq from anon, authenticated;
      grant usage, select on sequence public.despesas_id_seq to service_role;
    end if;

    alter table public.despesas alter column user_id set not null;

    if not exists (select 1 from pg_constraint where conname = 'despesas_user_id_fkey') then
      alter table public.despesas
        add constraint despesas_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;

    create index if not exists idx_despesas_user_id on public.despesas(user_id);
    create index if not exists idx_despesas_user_id_data on public.despesas(user_id, data);

    drop policy if exists despesas_owner_select on public.despesas;
    drop policy if exists despesas_owner_insert on public.despesas;
    drop policy if exists despesas_owner_update on public.despesas;
    drop policy if exists despesas_owner_delete on public.despesas;
  end if;

  -- investimentos
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'investimentos') then
    if exists (select 1 from public.investimentos where user_id is null) then
      raise exception 'public.investimentos contains rows with user_id null. Fix ownership before applying NOT NULL.';
    end if;

    alter table public.investimentos enable row level security;
    revoke all on table public.investimentos from anon, authenticated;
    grant select, insert, update, delete on table public.investimentos to service_role;

    if exists (select 1 from pg_class where relname = 'investimentos_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.investimentos_id_seq from anon, authenticated;
      grant usage, select on sequence public.investimentos_id_seq to service_role;
    end if;

    alter table public.investimentos alter column user_id set not null;

    if not exists (select 1 from pg_constraint where conname = 'investimentos_user_id_fkey') then
      alter table public.investimentos
        add constraint investimentos_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;

    create index if not exists idx_investimentos_user_id on public.investimentos(user_id);
    create index if not exists idx_investimentos_user_id_data on public.investimentos(user_id, data);
    create index if not exists idx_investimentos_user_id_data_fim on public.investimentos(user_id, data_fim);

    drop policy if exists investimentos_owner_select on public.investimentos;
    drop policy if exists investimentos_owner_insert on public.investimentos;
    drop policy if exists investimentos_owner_update on public.investimentos;
    drop policy if exists investimentos_owner_delete on public.investimentos;
  end if;

  -- controle_km
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_km') then
    if exists (select 1 from public.controle_km where user_id is null) then
      raise exception 'public.controle_km contains rows with user_id null. Fix ownership before applying NOT NULL.';
    end if;

    alter table public.controle_km enable row level security;
    revoke all on table public.controle_km from anon, authenticated;
    grant select, insert, update, delete on table public.controle_km to service_role;

    if exists (select 1 from pg_class where relname = 'controle_km_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.controle_km_id_seq from anon, authenticated;
      grant usage, select on sequence public.controle_km_id_seq to service_role;
    end if;

    alter table public.controle_km alter column user_id set not null;

    if not exists (select 1 from pg_constraint where conname = 'controle_km_user_id_fkey') then
      alter table public.controle_km
        add constraint controle_km_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;

    create index if not exists idx_controle_km_user_id on public.controle_km(user_id);
    create index if not exists idx_controle_km_user_id_periodo on public.controle_km(user_id, data_inicio, data_fim);

    drop policy if exists controle_km_owner_select on public.controle_km;
    drop policy if exists controle_km_owner_insert on public.controle_km;
    drop policy if exists controle_km_owner_update on public.controle_km;
    drop policy if exists controle_km_owner_delete on public.controle_km;
  end if;

  -- controle_litros
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_litros') then
    if exists (select 1 from public.controle_litros where user_id is null) then
      raise exception 'public.controle_litros contains rows with user_id null. Fix ownership before applying NOT NULL.';
    end if;

    alter table public.controle_litros enable row level security;
    revoke all on table public.controle_litros from anon, authenticated;
    grant select, insert, update, delete on table public.controle_litros to service_role;

    if exists (select 1 from pg_class where relname = 'controle_litros_id_seq' and relnamespace = 'public'::regnamespace) then
      revoke all on sequence public.controle_litros_id_seq from anon, authenticated;
      grant usage, select on sequence public.controle_litros_id_seq to service_role;
    end if;

    alter table public.controle_litros alter column user_id set not null;

    if not exists (select 1 from pg_constraint where conname = 'controle_litros_user_id_fkey') then
      alter table public.controle_litros
        add constraint controle_litros_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;

    create index if not exists idx_controle_litros_user_id on public.controle_litros(user_id);
    create index if not exists idx_controle_litros_user_id_data on public.controle_litros(user_id, data);

    drop policy if exists controle_litros_owner_select on public.controle_litros;
    drop policy if exists controle_litros_owner_insert on public.controle_litros;
    drop policy if exists controle_litros_owner_update on public.controle_litros;
    drop policy if exists controle_litros_owner_delete on public.controle_litros;
  end if;
end $$;

commit;
