begin;

alter table public.usuarios
  add column if not exists must_change_password boolean not null default false;

create table if not exists public.controle_km (
  id bigserial primary key,
  data_inicio date not null default current_date,
  data_fim date not null default current_date,
  km_total_rodado numeric not null default 0
);

create table if not exists public.controle_litros (
  id bigserial primary key,
  data date not null default current_date,
  litros numeric not null default 0
);

create table if not exists public.auth_sessions (
  session_id text primary key,
  user_id bigint not null,
  token_hash text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  revoked_at timestamptz,
  last_seen_at timestamptz,
  user_agent text
);

create index if not exists idx_auth_sessions_user_id on public.auth_sessions (user_id);
create index if not exists idx_auth_sessions_expires_at on public.auth_sessions (expires_at);

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

do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'usuarios'
      and column_name = 'id'
  ) then
    if not exists (select 1 from pg_constraint where conname = 'auth_sessions_user_id_fkey') then
      alter table public.auth_sessions
        add constraint auth_sessions_user_id_fkey
        foreign key (user_id) references public.usuarios(id) on delete cascade;
    end if;

    if not exists (select 1 from pg_constraint where conname = 'receitas_user_id_fkey') then
      alter table public.receitas
        add constraint receitas_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;
    if not exists (select 1 from pg_constraint where conname = 'despesas_user_id_fkey') then
      alter table public.despesas
        add constraint despesas_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;
    if not exists (select 1 from pg_constraint where conname = 'investimentos_user_id_fkey') then
      alter table public.investimentos
        add constraint investimentos_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;
    if not exists (select 1 from pg_constraint where conname = 'categorias_despesas_user_id_fkey') then
      alter table public.categorias_despesas
        add constraint categorias_despesas_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;
    if not exists (select 1 from pg_constraint where conname = 'controle_km_user_id_fkey') then
      alter table public.controle_km
        add constraint controle_km_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;
    if not exists (select 1 from pg_constraint where conname = 'controle_litros_user_id_fkey') then
      alter table public.controle_litros
        add constraint controle_litros_user_id_fkey
        foreign key (user_id) references public.usuarios(id);
    end if;
  end if;
end $$;

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

do $$
begin
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'receitas') then
    alter table public.receitas enable row level security;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'despesas') then
    alter table public.despesas enable row level security;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'investimentos') then
    alter table public.investimentos enable row level security;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'categorias_despesas') then
    alter table public.categorias_despesas enable row level security;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_km') then
    alter table public.controle_km enable row level security;
  end if;
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'controle_litros') then
    alter table public.controle_litros enable row level security;
  end if;
end $$;

commit;
