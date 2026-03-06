begin;

-- 1) Garantir coluna user_id nas tabelas de negócio.
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'receitas') then
    alter table public.receitas add column if not exists user_id bigint;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'despesas') then
    alter table public.despesas add column if not exists user_id bigint;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'investimentos') then
    alter table public.investimentos add column if not exists user_id bigint;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'categorias_despesas') then
    alter table public.categorias_despesas add column if not exists user_id bigint;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_km') then
    alter table public.controle_km add column if not exists user_id bigint;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_litros') then
    alter table public.controle_litros add column if not exists user_id bigint;
  end if;
end $$;

-- 2) Backfill seguro de user_id:
--    apenas quando houver exatamente 1 usuário em public.usuarios.
do $$
declare
  v_users_count int := 0;
  v_default_user_id bigint;
begin
  if not exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'usuarios') then
    raise notice 'Tabela public.usuarios não encontrada. Backfill de user_id ignorado.';
    return;
  end if;

  select count(*) into v_users_count from public.usuarios;
  if v_users_count <> 1 then
    raise notice 'Backfill automático ignorado: esperado 1 usuário em public.usuarios, encontrado %.', v_users_count;
    return;
  end if;

  select id into v_default_user_id from public.usuarios limit 1;

  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'receitas') then
    update public.receitas set user_id = v_default_user_id where user_id is null;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'despesas') then
    update public.despesas set user_id = v_default_user_id where user_id is null;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'investimentos') then
    update public.investimentos set user_id = v_default_user_id where user_id is null;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'categorias_despesas') then
    update public.categorias_despesas set user_id = v_default_user_id where user_id is null;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_km') then
    update public.controle_km set user_id = v_default_user_id where user_id is null;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_litros') then
    update public.controle_litros set user_id = v_default_user_id where user_id is null;
  end if;
end $$;

-- 3) Desabilitar RLS das tabelas de negócio (app não usa JWT do Supabase para user_id).
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'receitas') then
    alter table public.receitas disable row level security;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'despesas') then
    alter table public.despesas disable row level security;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'investimentos') then
    alter table public.investimentos disable row level security;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'categorias_despesas') then
    alter table public.categorias_despesas disable row level security;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_km') then
    alter table public.controle_km disable row level security;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_litros') then
    alter table public.controle_litros disable row level security;
  end if;
end $$;

-- 4) Índices úteis para filtros por usuário.
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'receitas') then
    create index if not exists idx_receitas_user_id on public.receitas(user_id);
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'despesas') then
    create index if not exists idx_despesas_user_id on public.despesas(user_id);
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'investimentos') then
    create index if not exists idx_investimentos_user_id on public.investimentos(user_id);
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'categorias_despesas') then
    create index if not exists idx_categorias_despesas_user_id on public.categorias_despesas(user_id);
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_km') then
    create index if not exists idx_controle_km_user_id on public.controle_km(user_id);
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_litros') then
    create index if not exists idx_controle_litros_user_id on public.controle_litros(user_id);
  end if;
end $$;

commit;
