# Operação

## Ambiente

O projeto roda com Streamlit e Supabase. O modo operacional esperado hoje é:

- `APP_DB_MODE=remote`

Se `SUPABASE_URL` ou `SUPABASE_KEY` estiverem ausentes, o app não deve iniciar em modo remoto.

## Variáveis de Configuração

Referência atual em `.env.example`:

- `APP_ENV`
- `APP_DB_MODE`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SESSION_TTL_DAYS`
- `SESSION_ROTATION_HOURS`

## Subida Local

```bash
streamlit run app.py
```

## Migrations do Supabase

Aplicar em ordem:

1. `sql/supabase_migration_2026_02_14.sql`
2. `sql/migrations/20260218_0900__security_sessions_user_ownership.sql`
3. `sql/migrations/20260305_1200__disable_rls_and_backfill_user_id.sql`
4. `sql/migrations/20260313_0900__reenable_rls_and_harden_privileges.sql`
5. `sql/migrations/20260316090000__align_rls_with_custom_auth_backend.sql`

Recomendação operacional:

- não pular a migration final de endurecimento de RLS;
- validar se as tabelas críticas existem antes de publicar;
- usar chave adequada ao runtime do backend.

## Comandos Úteis

Testes:

```bash
python3 -m unittest tests.test_repository
```

Checagem rápida de sintaxe:

```bash
python3 -m py_compile app.py core/auth.py UI/investimentos_ui.py repositories/base_repository.py
```

## Publicação

Antes do deploy, revisar:

- `APP_DB_MODE=remote`;
- credenciais válidas do Supabase;
- migrations aplicadas;
- ausência de arquivos sensíveis em versionamento;
- comportamento de login, logout e isolamento por usuário.
