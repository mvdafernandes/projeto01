begin;

do $$
begin
  if exists (select 1 from information_schema.tables where table_schema = 'public' and table_name = 'despesas') then
    alter table public.despesas add column if not exists recorrencia_tipo text;
    alter table public.despesas add column if not exists recorrencia_meses integer not null default 0;
    alter table public.despesas add column if not exists recorrencia_serie_id text;

    update public.despesas
    set recorrencia_tipo = coalesce(recorrencia_tipo, ''),
        recorrencia_meses = coalesce(recorrencia_meses, 0),
        recorrencia_serie_id = coalesce(recorrencia_serie_id, '');
  end if;
end $$;

commit;
