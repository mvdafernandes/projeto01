# Driver Analytics

Aplicação Streamlit para controle operacional e financeiro de motorista, com suporte a receitas, despesas, investimentos, métricas e autenticação com sessões no Supabase.

## Visão Geral

O projeto é organizado em camadas simples:

- `UI/`: páginas e componentes Streamlit.
- `services/`: orquestração de repositórios e cálculos.
- `repositories/`: acesso a dados e isolamento por `user_id`.
- `Metrics/`: funções analíticas puras.
- `core/`: configuração, autenticação, banco e segurança.
- `sql/`: schema base e migrations incrementais do Supabase.
- `tests/`: testes unitários focados em repositórios e isolamento.

Documentação complementar:

- [Arquitetura](docs/architecture.md)
- [Operação](docs/operations.md)
- [Segurança](docs/security.md)

## Funcionalidades

- Login com sessão remota em `auth_sessions`.
- Dashboard com métricas operacionais e financeiras.
- CRUD de receitas, despesas, categorias e investimentos.
- Módulo de investimentos com aportes, rendimentos, retiradas e simuladores.
- Isolamento de dados por usuário com `user_id`.

## Requisitos

- Python 3.11 ou superior.
- Projeto Supabase configurado.
- Variáveis de ambiente ou `secrets.toml` válidos.

## Configuração

Copie a referência de ambiente:

```bash
cp .env.example .env
```

Variáveis principais:

- `APP_ENV`: ambiente da aplicação. Use `dev` localmente.
- `APP_DB_MODE`: para o app atual, use `remote`.
- `SUPABASE_URL`: URL do projeto Supabase.
- `SUPABASE_KEY`: chave usada pelo backend Python.
- `SESSION_TTL_DAYS`: validade da sessão.
- `SESSION_ROTATION_HOURS`: janela de rotação da sessão.

## Banco e Migrations

O app assume Supabase remoto e valida o schema no bootstrap. Aplique o SQL base e depois as migrations em ordem:

1. `sql/supabase_migration_2026_02_14.sql`
2. `sql/migrations/20260218_0900__security_sessions_user_ownership.sql`
3. `sql/migrations/20260305_1200__disable_rls_and_backfill_user_id.sql`
4. `sql/migrations/20260313_0900__reenable_rls_and_harden_privileges.sql`
5. `sql/migrations/20260316_0900__align_rls_with_custom_auth_backend.sql`

Importante:

- as migrations de `2026-03-13` e `2026-03-16` compõem o endurecimento de segurança atual e devem permanecer aplicadas;
- o app depende de tabelas como `usuarios`, `auth_sessions`, `receitas`, `despesas` e `investimentos`.

## Execução

Instale as dependências do projeto conforme sua gestão de ambiente e inicie:

```bash
streamlit run app.py
```

## Testes e Validação

Testes existentes:

```bash
python3 -m unittest tests.test_repository
```

Verificação rápida de sintaxe:

```bash
python3 -m py_compile app.py core/auth.py UI/investimentos_ui.py
```

## Observações de Arquitetura

- A UI consome `DashboardService` como fachada.
- Os repositórios remotos falham de forma segura quando não há `user_id`.
- A autenticação mantém sessão ativa em memória do Streamlit e revalida no Supabase.
- O backend pode operar com chave de serviço; acesso direto de clientes deve respeitar RLS.
