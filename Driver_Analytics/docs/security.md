# Segurança

## Autenticação

A autenticação está centralizada em [core/auth.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/core/auth.py).

Características atuais:

- sessão validada no Supabase em `auth_sessions`;
- token de sessão não é persistido em querystring;
- sessão ativa mantida em `st.session_state`;
- logout revoga a sessão remota;
- rotação periódica de sessão;
- troca obrigatória de senha para `admin` inicial em ambiente de desenvolvimento.

## Senhas

O projeto usa hashing em [core/security/passwords.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/core/security/passwords.py), com suporte a upgrade de hashes legados quando necessário.

## Isolamento por Usuário

O isolamento de dados ocorre em duas camadas:

### Aplicação

[repositories/base_repository.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/repositories/base_repository.py) filtra leituras remotas por `user_id` e exige usuário autenticado para gravação.

Regra atual:

- usuário autenticado vê apenas os próprios dados;
- ausência de `user_id` não libera fallback global;
- leituras sem contexto retornam vazio ou falham de forma segura.

### Banco

As migrations de endurecimento mais recentes mantêm RLS habilitado, mas bloqueiam acesso direto de `anon` e `authenticated` às tabelas privadas porque a autenticação do projeto é própria e não prova integração com Supabase Auth do usuário final. O backend Python opera via `service_role`, e o isolamento funcional continua sendo reforçado também na camada de repositório.

Tabelas cobertas:

- `usuarios`
- `auth_sessions`
- `receitas`
- `despesas`
- `investimentos`
- `categorias_despesas`
- `controle_km`
- `controle_litros`

## Boas Práticas no Projeto

- não persistir credenciais na URL;
- não usar fallback que exponha dados de outros usuários;
- manter RLS habilitado nas tabelas multiusuário;
- restringir permissões de `anon` e `authenticated`;
- usar `service_role` apenas no backend;
- não depender de `auth.uid()` ou JWT claims do Supabase quando a autenticação do app for própria.

## Testes Relacionados

Os cenários mínimos de isolamento estão em [tests/test_repository.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/tests/test_repository.py).
