begin;

-- service_role bypasses RLS in Supabase, so explicit allow-all policies for it
-- are redundant and only add per-row policy evaluation overhead.
drop policy if exists usuarios_service_all on public.usuarios;
drop policy if exists auth_sessions_service_all on public.auth_sessions;

commit;
