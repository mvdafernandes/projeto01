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

commit;
