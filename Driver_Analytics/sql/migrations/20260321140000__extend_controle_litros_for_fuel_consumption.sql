begin;

alter table if exists public.controle_litros
  add column if not exists odometro numeric,
  add column if not exists valor_total numeric not null default 0,
  add column if not exists tanque_cheio boolean not null default false,
  add column if not exists tipo_combustivel text not null default '',
  add column if not exists observacao text not null default '';

create index if not exists idx_controle_litros_user_id_data_odometro
  on public.controle_litros(user_id, data, odometro);

commit;
