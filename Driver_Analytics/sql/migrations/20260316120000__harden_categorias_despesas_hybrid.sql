begin;

-- categorias_despesas follows a hybrid model:
-- - system categories: user_id is null
-- - user custom categories: user_id is not null
-- The backend reads global + current-user categories and writes only user-owned rows.

alter table if exists public.categorias_despesas enable row level security;

-- Client-facing roles do not access this table directly.
revoke all on table public.categorias_despesas from anon, authenticated;
grant select, insert, update, delete on table public.categorias_despesas to service_role;

do $$
begin
  if exists (select 1 from pg_class where relname = 'categorias_despesas_id_seq' and relnamespace = 'public'::regnamespace) then
    revoke all on sequence public.categorias_despesas_id_seq from anon, authenticated;
    grant usage, select on sequence public.categorias_despesas_id_seq to service_role;
  end if;
end $$;

-- Remove legacy ownership policies that assumed direct client filtering.
drop policy if exists categorias_owner_select on public.categorias_despesas;
drop policy if exists categorias_owner_insert on public.categorias_despesas;
drop policy if exists categorias_owner_update on public.categorias_despesas;
drop policy if exists categorias_owner_delete on public.categorias_despesas;

-- Keep user_id nullable for the hybrid model and ensure backend ownership integrity.
alter table public.categorias_despesas
  alter column nome set not null;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'categorias_despesas_user_id_fkey') then
    alter table public.categorias_despesas
      add constraint categorias_despesas_user_id_fkey
      foreign key (user_id) references public.usuarios(id);
  end if;
end $$;

-- Replace legacy global uniqueness with explicit global-vs-user uniqueness.
alter table public.categorias_despesas
  drop constraint if exists ux_categorias_despesas_nome;

drop index if exists public.ux_categorias_despesas_nome_ci;

create index if not exists idx_categorias_despesas_user_id
  on public.categorias_despesas (user_id);

create unique index if not exists ux_categorias_despesas_global_nome_ci
  on public.categorias_despesas (lower(trim(nome)))
  where user_id is null;

create unique index if not exists ux_categorias_despesas_user_nome_ci
  on public.categorias_despesas (user_id, lower(trim(nome)))
  where user_id is not null;

commit;
