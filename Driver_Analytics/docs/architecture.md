# Arquitetura

## Estrutura

### UI

Os arquivos em `UI/` implementam páginas e componentes Streamlit. O ponto de entrada é [app.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/app.py), que:

- configura o layout;
- exige autenticação;
- valida o modo remoto;
- roteia entre Dashboard, Cadastros, Receitas, Despesas e Investimentos.

### Services

[services/dashboard_service.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/services/dashboard_service.py) funciona como fachada da aplicação. Ele:

- instancia os repositórios;
- centraliza validações de alto nível;
- evita duplicidade de regras entre páginas;
- expõe operações consumidas pela UI.

### Repositories

Os repositórios em `repositories/` encapsulam o acesso ao Supabase e a normalização dos `DataFrame`s.

Pontos centrais:

- [repositories/base_repository.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/repositories/base_repository.py) resolve `user_id` atual;
- leituras remotas são estritamente filtradas por `user_id`;
- escritas anexam `user_id` ao payload;
- ausência de usuário autenticado falha de forma segura.

### Metrics

As métricas ficam separadas em serviços e funções puras:

- [services/metrics_service.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/services/metrics_service.py)
- `Metrics/analytics_*.py`

Essa separação permite que a UI monte dashboards sem misturar cálculo com apresentação.

### Core

`core/` concentra infraestrutura:

- [core/config.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/core/config.py): configuração e cache.
- [core/database.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/core/database.py): cliente Supabase.
- [core/auth.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/core/auth.py): autenticação, sessão, rotação, logout e troca obrigatória de senha.

## Fluxo de Dados

1. A UI chama métodos do `DashboardService`.
2. O service consulta ou persiste dados via repositórios.
3. Os repositórios usam Supabase e normalizam o retorno.
4. A UI apresenta tabelas, KPIs e gráficos.

## Convenções Relevantes

- Colunas vindas do banco podem ser convertidas entre nomes internos e nomes usados na UI.
- Datas e valores numéricos são sanitizados antes do consumo analítico.
- O projeto favorece `DataFrame` como contrato entre repositório, serviço e UI.

## Módulo de Investimentos

[UI/investimentos_ui.py](/Users/marcus/Documents/GitHub/Projeto01/Driver_Analytics/UI/investimentos_ui.py) segue o padrão das demais telas:

- resumo da carteira;
- gráficos de evolução e composição;
- simulador da carteira;
- simulador personalizado;
- CRUD de aportes, rendimentos e retiradas.
