# Changelog

## 2026-03-13

- Security: added `sql/migrations/20260313_0900__reenable_rls_and_harden_privileges.sql` to re-enable RLS after legacy relaxations, restrict anon access, and define explicit owner policies for user-owned tables.
- Security: tightened Supabase auth/session guidance in the app bootstrap to include the new RLS hardening migration.
- Docs: added `README.md` plus documentation for architecture, operations and security under `docs/`.

## 2026-03-16

- Security: added `sql/migrations/20260316_0900__align_rls_with_custom_auth_backend.sql` to remove claim-based RLS assumptions and lock private tables to backend `service_role` access only, consistent with the project's custom authentication model.

## 2026-02-18

- Security: removed session token from querystring persistence and kept authentication restricted to in-memory Streamlit session state plus server-side sessions with token hash, TTL, rotation and revocation.
- Security: default `admin/admin` is now created only when `APP_ENV=dev`, with forced password change on first login.
- Security: added `core/security/passwords.py` with Argon2id hashing (bcrypt fallback) and upgrade-in-place from legacy hashes.
- Security: added login and password-recovery rate limiting with neutral response for recovery.
- Data ownership: added `user_id` handling in repositories for read/write filtering.
- Schema: local SQLite now includes `must_change_password`, `auth_sessions`, `auth_rate_limits`, and ownership indexes.
- Infra: added `.env.example`, `pyproject.toml`, `.pre-commit-config.yaml`, and GitHub Actions CI workflow.
- UX: app now warns when running `APP_DB_MODE=auto` without Supabase connection (local fallback mode).
