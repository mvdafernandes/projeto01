begin;

-- =============================================
-- 1) Tabela de categorias de despesas
-- =============================================
create table if not exists public.categorias_despesas (
  id bigserial primary key,
  nome text not null,
  constraint ux_categorias_despesas_nome unique (nome)
);

create unique index if not exists ux_categorias_despesas_nome_ci
  on public.categorias_despesas (lower(trim(nome)));

-- Seed opcional de categorias
insert into public.categorias_despesas (nome)
values
  ('Combustível'),
  ('Alimentação'),
  ('Manutenção'),
  ('Lavagem'),
  ('Seguro'),
  ('Outros')
on conflict do nothing;

-- =============================================
-- 2) Investimentos com categoria obrigatória
-- =============================================
alter table public.investimentos
  add column if not exists categoria text;

update public.investimentos
set categoria = coalesce(nullif(trim(categoria), ''), 'Renda Fixa')
where categoria is null or trim(categoria) = '';

alter table public.investimentos
  alter column categoria set not null;

alter table public.investimentos
  drop constraint if exists ck_investimentos_categoria_valida;

alter table public.investimentos
  add constraint ck_investimentos_categoria_valida
  check (categoria in ('Renda Fixa', 'Renda Variável'));

create index if not exists idx_investimentos_categoria
  on public.investimentos (categoria);

-- =============================================
-- 3) Usuários para recuperação de senha
-- =============================================
alter table public.usuarios
  add column if not exists cpf text,
  add column if not exists nome_completo text,
  add column if not exists data_nascimento date,
  add column if not exists pergunta_secreta text,
  add column if not exists resposta_secreta_hash text;

create unique index if not exists ux_usuarios_cpf
  on public.usuarios (cpf)
  where cpf is not null and trim(cpf) <> '';

-- =============================================
-- 4) Regras anti-duplicidade + índices
-- =============================================
create index if not exists idx_receitas_data on public.receitas(data);
create index if not exists idx_despesas_data on public.despesas(data);
create index if not exists idx_investimentos_data on public.investimentos(data);

create unique index if not exists ux_receitas_natural
  on public.receitas (data, valor, km, tempo_trabalhado);

create unique index if not exists ux_despesas_natural
  on public.despesas (data, lower(trim(categoria)), valor);

-- Compatível com o schema atual do projeto (sem coluna ativo dedicada)
create unique index if not exists ux_investimentos_natural
  on public.investimentos (data, categoria, aporte, rendimento);

-- =============================================
-- 5) Recorte temporal e tipo de movimentação (investimentos)
-- =============================================
alter table public.investimentos
  add column if not exists data_inicio date,
  add column if not exists data_fim date,
  add column if not exists tipo_movimentacao text;

update public.investimentos
set
  data_inicio = coalesce(data_inicio, data),
  data_fim = coalesce(data_fim, data),
  tipo_movimentacao = coalesce(
    nullif(trim(tipo_movimentacao), ''),
    case
      when coalesce(aporte, 0) > 0 then 'APORTE'
      when coalesce(aporte, 0) < 0 then 'RETIRADA'
      else 'RENDIMENTO'
    end
  );

alter table public.investimentos
  alter column data_inicio set not null;

alter table public.investimentos
  alter column data_fim set not null;

alter table public.investimentos
  alter column tipo_movimentacao set not null;

alter table public.investimentos
  drop constraint if exists ck_investimentos_tipo_movimentacao;

alter table public.investimentos
  add constraint ck_investimentos_tipo_movimentacao
  check (tipo_movimentacao in ('APORTE', 'RENDIMENTO', 'RETIRADA'));

alter table public.investimentos
  drop constraint if exists ck_investimentos_periodo_valido;

alter table public.investimentos
  add constraint ck_investimentos_periodo_valido
  check (data_fim >= data_inicio);

create index if not exists idx_investimentos_data_inicio
  on public.investimentos (data_inicio);

create index if not exists idx_investimentos_data_fim
  on public.investimentos (data_fim);

create index if not exists idx_investimentos_tipo_movimentacao
  on public.investimentos (tipo_movimentacao);

-- =============================================
-- 6) Eficiência operacional (KM total e litros)
-- =============================================
alter table public.receitas
  add column if not exists km_rodado_total numeric not null default 0;

update public.receitas
set km_rodado_total = coalesce(km_rodado_total, km, 0);

alter table public.despesas
  add column if not exists litros numeric not null default 0;

update public.despesas
set litros = coalesce(litros, 0);

create table if not exists public.controle_km (
  id bigserial primary key,
  data_inicio date not null,
  data_fim date not null,
  km_total_rodado numeric not null default 0
);

alter table public.controle_km
  add column if not exists data_inicio date,
  add column if not exists data_fim date;

update public.controle_km
set
  data_inicio = coalesce(data_inicio, data_fim, current_date),
  data_fim = coalesce(data_fim, data_inicio, current_date);

create index if not exists idx_controle_km_data_inicio
  on public.controle_km (data_inicio);

create index if not exists idx_controle_km_data_fim
  on public.controle_km (data_fim);

create table if not exists public.controle_litros (
  id bigserial primary key,
  data date not null,
  litros numeric not null default 0
);

create index if not exists idx_controle_litros_data
  on public.controle_litros (data);

-- =============================================
-- 7) Segurança: usuários, sessões e ownership
-- =============================================
alter table public.usuarios
  add column if not exists must_change_password boolean not null default false;

create table if not exists public.auth_sessions (
  session_id text primary key,
  user_id bigint not null references public.usuarios(id) on delete cascade,
  token_hash text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  revoked_at timestamptz,
  last_seen_at timestamptz,
  user_agent text
);

create index if not exists idx_auth_sessions_user_id
  on public.auth_sessions (user_id);

create index if not exists idx_auth_sessions_expires_at
  on public.auth_sessions (expires_at);

alter table public.receitas add column if not exists user_id bigint references public.usuarios(id);
alter table public.despesas add column if not exists user_id bigint references public.usuarios(id);
alter table public.investimentos add column if not exists user_id bigint references public.usuarios(id);
alter table public.categorias_despesas add column if not exists user_id bigint references public.usuarios(id);
alter table public.controle_km add column if not exists user_id bigint references public.usuarios(id);
alter table public.controle_litros add column if not exists user_id bigint references public.usuarios(id);

create index if not exists idx_receitas_user_id on public.receitas(user_id);
create index if not exists idx_despesas_user_id on public.despesas(user_id);
create index if not exists idx_investimentos_user_id on public.investimentos(user_id);
create index if not exists idx_categorias_despesas_user_id on public.categorias_despesas(user_id);
create index if not exists idx_controle_km_user_id on public.controle_km(user_id);
create index if not exists idx_controle_litros_user_id on public.controle_litros(user_id);

alter table public.receitas enable row level security;
alter table public.despesas enable row level security;
alter table public.investimentos enable row level security;
alter table public.categorias_despesas enable row level security;
alter table public.controle_km enable row level security;
alter table public.controle_litros enable row level security;

drop policy if exists receitas_owner_select on public.receitas;
drop policy if exists receitas_owner_insert on public.receitas;
drop policy if exists receitas_owner_update on public.receitas;
drop policy if exists receitas_owner_delete on public.receitas;
create policy receitas_owner_select on public.receitas for select using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy receitas_owner_insert on public.receitas for insert with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy receitas_owner_update on public.receitas for update using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id) with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy receitas_owner_delete on public.receitas for delete using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);

drop policy if exists despesas_owner_select on public.despesas;
drop policy if exists despesas_owner_insert on public.despesas;
drop policy if exists despesas_owner_update on public.despesas;
drop policy if exists despesas_owner_delete on public.despesas;
create policy despesas_owner_select on public.despesas for select using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy despesas_owner_insert on public.despesas for insert with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy despesas_owner_update on public.despesas for update using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id) with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy despesas_owner_delete on public.despesas for delete using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);

drop policy if exists investimentos_owner_select on public.investimentos;
drop policy if exists investimentos_owner_insert on public.investimentos;
drop policy if exists investimentos_owner_update on public.investimentos;
drop policy if exists investimentos_owner_delete on public.investimentos;
create policy investimentos_owner_select on public.investimentos for select using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy investimentos_owner_insert on public.investimentos for insert with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy investimentos_owner_update on public.investimentos for update using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id) with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy investimentos_owner_delete on public.investimentos for delete using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);

drop policy if exists categorias_owner_select on public.categorias_despesas;
drop policy if exists categorias_owner_insert on public.categorias_despesas;
drop policy if exists categorias_owner_update on public.categorias_despesas;
drop policy if exists categorias_owner_delete on public.categorias_despesas;
create policy categorias_owner_select on public.categorias_despesas for select using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy categorias_owner_insert on public.categorias_despesas for insert with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy categorias_owner_update on public.categorias_despesas for update using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id) with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy categorias_owner_delete on public.categorias_despesas for delete using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);

drop policy if exists controle_km_owner_select on public.controle_km;
drop policy if exists controle_km_owner_insert on public.controle_km;
drop policy if exists controle_km_owner_update on public.controle_km;
drop policy if exists controle_km_owner_delete on public.controle_km;
create policy controle_km_owner_select on public.controle_km for select using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy controle_km_owner_insert on public.controle_km for insert with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy controle_km_owner_update on public.controle_km for update using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id) with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy controle_km_owner_delete on public.controle_km for delete using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);

drop policy if exists controle_litros_owner_select on public.controle_litros;
drop policy if exists controle_litros_owner_insert on public.controle_litros;
drop policy if exists controle_litros_owner_update on public.controle_litros;
drop policy if exists controle_litros_owner_delete on public.controle_litros;
create policy controle_litros_owner_select on public.controle_litros for select using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy controle_litros_owner_insert on public.controle_litros for insert with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy controle_litros_owner_update on public.controle_litros for update using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id) with check (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);
create policy controle_litros_owner_delete on public.controle_litros for delete using (coalesce(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'user_id', '-1')::bigint = user_id);

commit;
