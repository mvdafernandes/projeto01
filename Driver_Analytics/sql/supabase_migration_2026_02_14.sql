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

commit;
