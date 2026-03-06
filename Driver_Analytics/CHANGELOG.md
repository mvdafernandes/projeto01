# Changelog

## 2026-02-18

- Security: removed session token via querystring and introduced server-side sessions with token hash, TTL, rotation and revocation.
- Security: default `admin/admin` is now created only when `APP_ENV=dev`, with forced password change on first login.
- Security: added `core/security/passwords.py` with Argon2id hashing (bcrypt fallback) and upgrade-in-place from legacy hashes.
- Security: added login and password-recovery rate limiting with neutral response for recovery.
- Data ownership: added `user_id` handling in repositories for read/write filtering.
- Schema: local SQLite now includes `must_change_password`, `auth_sessions`, `auth_rate_limits`, and ownership indexes.
- Infra: added `.env.example`, `pyproject.toml`, `.pre-commit-config.yaml`, and GitHub Actions CI workflow.
- UX: app now warns when running `APP_DB_MODE=auto` without Supabase connection (local fallback mode).
