begin;

-- Fix mutable search_path warnings on helper and trigger functions without
-- changing business logic or introducing client-side bypasses.
do $$
declare
  fn record;
begin
  for fn in
    select
      n.nspname as schema_name,
      p.proname as function_name,
      pg_get_function_identity_arguments(p.oid) as identity_args
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where (n.nspname, p.proname) in (
      ('app', 'current_user_id'),
      ('public', 'app_current_user_id'),
      ('public', 'fn_investimentos_defaults'),
      ('public', 'set_work_days_updated_at'),
      ('public', 'set_work_km_periods_updated_at')
    )
  loop
    execute format(
      'alter function %I.%I(%s) set search_path = '''';',
      fn.schema_name,
      fn.function_name,
      fn.identity_args
    );
  end loop;
end;
$$;

commit;
