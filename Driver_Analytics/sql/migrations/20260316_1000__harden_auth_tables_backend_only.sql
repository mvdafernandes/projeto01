begin;

-- Auth tables are backend-only in this project.
-- End users do not authenticate with Supabase Auth; login is handled by the
-- Python application against public.usuarios and public.auth_sessions.

-- Keep RLS enabled so the default posture remains restrictive.
alter table if exists public.usuarios enable row level security;
alter table if exists public.auth_sessions enable row level security;

-- Remove legacy/incoherent policies that assumed direct client access.
drop policy if exists usuarios_self_select on public.usuarios;
drop policy if exists usuarios_self_update on public.usuarios;
drop policy if exists auth_sessions_self_select on public.auth_sessions;
drop policy if exists auth_sessions_self_update on public.auth_sessions;
drop policy if exists auth_sessions_self_delete on public.auth_sessions;

-- Remove broad grants from client-facing roles.
revoke all on table public.usuarios from anon, authenticated;
revoke all on table public.auth_sessions from anon, authenticated;

-- Keep backend access through the privileged Supabase key used by the app.
grant select, insert, update, delete on table public.usuarios to service_role;
grant select, insert, update, delete on table public.auth_sessions to service_role;

-- Restrict sequence access for user creation to the backend only.
revoke all on sequence public.usuarios_id_seq from anon, authenticated;
grant usage, select on sequence public.usuarios_id_seq to service_role;

commit;
