begin;

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

create index if not exists idx_auth_sessions_user_id on public.auth_sessions (user_id);
create index if not exists idx_auth_sessions_expires_at on public.auth_sessions (expires_at);

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

commit;
