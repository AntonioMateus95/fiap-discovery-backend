# Contabilizei — Analytics Assistant

## Visão Geral

Aplicação de analytics conversacional. O usuário faz uma pergunta em linguagem natural; um pipeline a transforma em uma consulta SQL executada no ClickHouse e devolve uma resposta textual em linguagem natural.

O repositório contém **duas implementações do mesmo pipeline**, mantidas em paralelo:

- **`v1/`** — orquestrado visualmente pelo [Langflow](https://www.langflow.org/). O fluxo roda a partir de `langflow_config/langflow.db`, um SQLite **não versionado** (estado local/gerado): na primeira subida do container, sem `langflow.db` existente, o entrypoint (`v1/entrypoint.sh`) importa automaticamente o export mais recente em `v1/langflow/*.json` (nome: **Contabilizei**). Cada etapa do pipeline é um nó Langflow; a lógica customizada vive em `v1/components/*.py` como subclasses de `Component`.
- **`v2/`** — reimplementação do mesmo pipeline como código Python puro (LangChain + Starlette), exposta como API REST (`POST /query`), sem depender do runtime do Langflow.

As duas versões compartilham o mesmo catálogo semântico, os mesmos prompts de LLM (Groq) e a mesma infraestrutura de dados (MinIO + ClickHouse). Ao alterar regras de negócio (prompts, catálogo, lógica de geração de SQL), avalie se a mudança precisa ser replicada nos dois lados — os arquivos são independentes, não compartilhados por import.

Contexto de negócio do desafio: ver `PROBLEM.md`.

---

## Infraestrutura comum

| Serviço      | Imagem                              | Porta(s)                | Função                                  | Usado por |
|--------------|--------------------------------------|--------------------------|------------------------------------------|-----------|
| `minio`      | `minio/minio`                       | 9000, 9001                | Object storage (dados raw CNPJ/Receita) | v1, v2    |
| `clickhouse` | `clickhouse/clickhouse-server`      | 8123 (HTTP), 9002 (TCP)   | Banco de dados analítico                | v1, v2    |
| `langflow`   | `v1/langflow.dockerfile` (customizado) | 7860                    | Orquestrador do pipeline (UI + runtime) | v1 apenas |

Credenciais padrão: `admin` / `password123`. Banco ClickHouse: `contabilizei`. Tabela analítica principal: `contabilizei.abertura_empresas_parquet` (populada via `S3 Engine`, DDL em `clickhouse_config/init.sql`).

- v1: `docker compose -f v1/docker-compose.yml up -d` (sobe minio + clickhouse + langflow). Na primeira execução (sem `langflow_config/langflow.db` local), o container do Langflow importa automaticamente o fluxo Contabilizei — ver seção "Bootstrap do fluxo (primeira execução)".
- v2: `docker compose -f v2/infra.yml up -d` (sobe só minio + clickhouse; a API roda fora de container, ver seção v2).

---

## v1 — Langflow

### Bootstrap do fluxo (primeira execução)

`langflow_config/langflow.db` não é versionado (ver `.gitignore`) — é estado local, recriado pelo próprio Langflow. Para que quem clona o repositório pela primeira vez já suba com o fluxo Contabilizei pronto, sem precisar importar manualmente pela UI:

- **`v1/entrypoint.sh`**: entrypoint do container `langflow`. Antes de rodar `langflow run`, verifica se `$LANGFLOW_CONFIG_DIR/langflow.db` já existe. Se **não** existir (primeira subida, `langflow_config/` vazio ou ausente), exporta `LANGFLOW_LOAD_FLOWS_PATH=/app/default_flows` para que o Langflow importe automaticamente o fluxo ao inicializar. Se o arquivo **já** existir (subidas seguintes), a variável não é definida e o import é pulado — isso preserva qualquer edição feita na UI e evita um bug conhecido do Langflow que trava a inicialização ao reimportar um fluxo já existente no banco.
- **`v1/langflow.dockerfile`**: copia `v1/langflow/V202606160017__correcao_tipo_input_componentes_sql.json` (o export mais recente) para `/app/default_flows/contabilizei.json` na imagem, e define `ENTRYPOINT ["/app/entrypoint.sh"]` mantendo `CMD ["langflow", "run"]`.

Ao gerar um novo export versionado em `v1/langflow/` (ver seção "Estrutura de Arquivos"), atualize também o `COPY` em `v1/langflow.dockerfile` para apontar para o arquivo mais recente.

Se quiser forçar uma reimportação do fluxo padrão (ex.: para descartar edições locais feitas na UI), apague `langflow_config/langflow.db` e suba o container novamente.

### Pipeline — Fluxo de Dados

O fluxo possui dois caminhos dependendo do resultado do Planner:

```
[Schema JSON]──────────────────────────────────────────┐
                                                        ▼
[Catálogo semântico base] ──► [Montagem do catálogo] ──► [Parser] ──► [Prompt Template (Planner)]
[Read File: abertura_empresas.yaml] ─────────────────────────────────────►│
                                                                           │ system_message
[Chat Input] ────────────────────────────────────────────────────────────►│
(pergunta do usuário)                                                      ▼
                                                                   [Groq LLM — Planner]
                                                                   llama-3.3-70b-versatile
                                                                   temperature: 0.1
                                                                           │
                                                                           ▼
                                                                   [Validar intent]
                                                                   intent == "unknown"?
                                               ┌────── true ───────────────┤
                                               ▼                           │ false
                                    [Text Operations]                      ▼
                                    (regex replace →              [SQL Query Builder]
                                    mensagem de fallback)         JSON → SQL (SQLAlchemy)
                                               │                           │
                                               ▼                           ▼
                                    [Chat Output ①]              [SQL Database]
                                    (intent desconhecido)        Executa no ClickHouse
                                                                           │
                                    [Chat Input] ─────────────────────────┤ (user_prompt)
                                                                           ▼
                                                                   [Parser: DataFrame → texto]
                                                                           │ query_result
                                                                           ▼
                                                                   [Prompt Template (Deliver)]
                                                                   {user_prompt} + {query_result}
                                                                           │
                                                                           ▼
                                                                   [Groq LLM — Deliver]
                                                                   llama-3.3-70b-versatile
                                                                   temperature: 0.1
                                                                           │
                                                                           ▼
                                                                   [Chat Output ②]
                                                                   (resposta final)
```

### Nós do Fluxo Langflow

| Node ID                       | Nome no UI                           | Tipo                   | Posição (x, y)  |
|-------------------------------|--------------------------------------|------------------------|-----------------|
| `TextInput-AYh8e`             | Schema json para o planner           | TextInput              | (108, -38)      |
| `TextInput-cl2BX`             | Catálogo semântico genérico          | TextInput              | (107, 241)      |
| `File-hMTWH`                  | Read File                            | File                   | (107, 548)      |
| `PythonREPLComponent-pJ2PO`   | Montagem do catálogo semântico final | PythonREPLComponent    | (732, 307)      |
| `ParserComponent-G4kjh`       | Parser (catálogo → texto)            | ParserComponent        | (1247, 438)     |
| `Prompt Template-6MOT3`       | Prompt Template (Planner)            | Prompt Template        | (1733, 108)     |
| `ChatInput-lmSIT`             | Chat Input                           | ChatInput              | (1656, -349)    |
| `GroqModel-plHGP`             | Groq — Planner                       | GroqModel              | (2201, -77)     |
| `PythonREPLComponent-1s7YW`   | Validar intent                       | PythonREPLComponent    | (2679, 134)     |
| `TextOperations-RpUyu`        | Text Operations (fallback)           | TextOperations         | (3635, -334)    |
| `ChatOutput-Vk7t0`            | Chat Output ① (intent unknown)      | ChatOutput             | (4183, -8)      |
| `PythonREPLComponent-Mwems`   | SQL Query Builder                    | PythonREPLComponent    | (3175, 377)     |
| `SQLComponent-jrGT7`          | SQL Database                         | SQLComponent            | (3617, 391)     |
| `ParserComponent-XHlBw`       | Parser (DataFrame → texto)           | ParserComponent        | (4005, 543)     |
| `Prompt Template-hr0Il`       | Prompt Template (Deliver)            | Prompt Template        | (4476, 239)     |
| `GroqModel-v4rce`             | Groq — Deliver                       | GroqModel              | (4970, 258)     |
| `ChatOutput-9Npsa`            | Chat Output ② (resposta final)      | ChatOutput             | (5489, 491)     |

### Arestas do Fluxo (Conexões)

| De (node → output)                              | Para (node → input)                              |
|-------------------------------------------------|--------------------------------------------------|
| `TextInput-cl2BX` → `text`                      | `PythonREPLComponent-pJ2PO` → `semantic_catalog` |
| `File-hMTWH` → `path`                           | `PythonREPLComponent-pJ2PO` → `dataset`          |
| `PythonREPLComponent-pJ2PO` → `result`          | `ParserComponent-G4kjh` → `input_data`           |
| `ParserComponent-G4kjh` → `parsed_text`         | `Prompt Template-6MOT3` → `semantic_catalog`     |
| `TextInput-AYh8e` → `text`                      | `Prompt Template-6MOT3` → `json_schema`          |
| `Prompt Template-6MOT3` → `prompt`              | `GroqModel-plHGP` → `system_message`             |
| `ChatInput-lmSIT` → `message`                   | `GroqModel-plHGP` → `input_value`                |
| `GroqModel-plHGP` → `text_output`               | `PythonREPLComponent-1s7YW` → `query_plan`       |
| `PythonREPLComponent-1s7YW` → `true_result`     | `TextOperations-RpUyu` → `text_input`            |
| `PythonREPLComponent-1s7YW` → `false_result`    | `PythonREPLComponent-Mwems` → `query_plan`       |
| `TextOperations-RpUyu` → `message`              | `ChatOutput-Vk7t0` → `input_value`               |
| `PythonREPLComponent-Mwems` → `result`          | `SQLComponent-jrGT7` → `query`                   |
| `SQLComponent-jrGT7` → `run_sql_query`          | `ParserComponent-XHlBw` → `input_data`           |
| `ParserComponent-XHlBw` → `parsed_text`         | `Prompt Template-hr0Il` → `query_result`         |
| `ChatInput-lmSIT` → `message`                   | `Prompt Template-hr0Il` → `user_prompt`          |
| `Prompt Template-hr0Il` → `prompt`              | `GroqModel-v4rce` → `input_value`                |
| `GroqModel-v4rce` → `text_output`               | `ChatOutput-9Npsa` → `input_value`               |

### Componentes Detalhados

#### 1. Inputs estáticos

- **`TextInput-AYh8e` — Schema json para o planner**: contém o JSON Schema completo (`v1/planner/planner.schema.json`) injetado como variável `{json_schema}` no prompt do Planner.
- **`TextInput-cl2BX` — Catálogo semântico genérico**: contém o conteúdo de `v1/base_semantic_catalog.yaml`.
- **`File-hMTWH` — Read File**: lê o arquivo `abertura_empresas` (YAML do dataset) do storage local e passa o caminho para o componente de montagem do catálogo.

#### 2. Montagem do Catálogo Semântico
**Arquivo:** `v1/components/semantic_catalog_builder_component.py`
**Node:** `PythonREPLComponent-pJ2PO`

Mescla o catálogo base (`v1/base_semantic_catalog.yaml`) com o dataset YAML lido pelo `File-hMTWH`, populando a chave `datasets` no YAML final. O resultado é passado para um `Parser` que o serializa como texto puro antes de entrar no Prompt Template.

#### 3. Planner (LLM)
**Arquivos:** `v1/planner/system_prompt.txt`, `v1/planner/planner.schema.json`
**Nodes:** `Prompt Template-6MOT3` + `GroqModel-plHGP`

**Modelo:** `llama-3.3-70b-versatile` via Groq API (`https://api.groq.com`)
**Temperature:** `0.1`

O Prompt Template monta o system message com duas variáveis:
- `{json_schema}` — JSON Schema que define o formato obrigatório da resposta
- `{semantic_catalog}` — Catálogo semântico completo com datasets, campos e métricas

A pergunta do usuário chega via `ChatInput` como `input_value`.

**Responsabilidade do Planner:** converter a pergunta em linguagem natural em um **JSON estruturado**, nunca em SQL. Regras fundamentais:
- Usa apenas elementos definidos no catálogo semântico.
- Se a pergunta exigir algo fora do catálogo, retorna `{"intent": "unknown"}`.
- Nunca escreve explicações, nunca usa blocos de código Markdown.

**Intents possíveis:**

| Intent        | Uso                                              |
|---------------|--------------------------------------------------|
| `aggregation` | Volume total, consolidação, resumo               |
| `ranking`     | Ordenação por maior/menor valor agregado         |
| `timeseries`  | Evolução temporal                                |
| `lookup`      | Detalhe ou busca específica                      |
| `comparison`  | Comparação entre grupos, períodos ou segmentos   |
| `unknown`     | Pergunta fora do escopo do catálogo              |

**Estrutura do JSON de saída** (`planner.schema.json` — idêntico em `v1/planner/` e `v2/assets/planner_schema.json`):

```jsonc
{
  "intent": "aggregation | ranking | timeseries | lookup | comparison | unknown",
  "table": "schema.tabela_fisica",
  "select": [
    { "kind": "dimension", "field": "uf", "alias": "estado" },
    { "kind": "aggregated_field", "field": "*", "aggregation": "count", "alias": "total" }
  ],
  "filters": [
    { "field": "ano_mes", "operator": "between", "value": { "start": "202401", "end": "202412" } }
  ],
  "group_by": ["uf"],
  "order_by": [{ "field": "total", "direction": "desc" }],
  "limit": 27,
  "time_grain": "month | year | quarter | week | day | none | null"
}
```

Agregações: `count`, `count_distinct`, `sum`, `avg`, `min`, `max`.
Operadores de filtro: `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `ilike`, `in`, `not_in`, `between`, `is_null`, `is_not_null`.

#### 4. Validar Intent
**Arquivo:** `v1/components/validate_intent_component.py`
**Node:** `PythonREPLComponent-1s7YW`

Roteador condicional. Verifica se `intent == "unknown"` no JSON do Planner.

- **`true_result`** (intent desconhecido) → `TextOperations-RpUyu` → `ChatOutput-Vk7t0`
- **`false_result`** (intent reconhecido) → `PythonREPLComponent-Mwems` (SQL Query Builder)

#### 5. Fallback (intent unknown)
**Node:** `TextOperations-RpUyu`

Usa substituição via regex (`^.+$`) para substituir qualquer texto pela mensagem fixa de fallback:

> *"Não foi possível responder à sua pergunta com o conhecimento que tenho no momento. Tente novamente mais tarde."*

A saída vai para `ChatOutput-Vk7t0` encerrando o fluxo.

#### 6. SQL Query Builder
**Arquivo:** `v1/components/sql_query_builder_component.py`
**Node:** `PythonREPLComponent-Mwems`

Converte o JSON do Planner em SQL executável usando **SQLAlchemy Core**. Recebe `database_url` como parâmetro de entrada para introspeccionar o schema da tabela em tempo de execução.

**Processo interno (`JsonToSqlBuilder`):**
1. Introspecciona colunas da tabela via `autoload_with` do SQLAlchemy (conecta ao ClickHouse).
2. Constrói expressões `SELECT` (dimensões ou agregações).
3. Aplica filtros com `AND` implícito.
4. Adiciona `GROUP BY`, `ORDER BY` e `LIMIT`.
5. Limpa blocos de código Markdown caso o LLM os inclua acidentalmente.
6. Compila e retorna a SQL como string com literal binds.

A mesma lógica (classe `JsonToSqlBuilder`) é reimplementada, sem o wrapper `Component` do Langflow, em `v2/components/sql_builder.py`.

#### 7. Execução no ClickHouse
**Node:** `SQLComponent-jrGT7`

Executa o SQL gerado pelo Query Builder diretamente no ClickHouse, contra `contabilizei.abertura_empresas_parquet`. O resultado é um `DataFrame` que passa por um `Parser` (modo Stringify, template `{sql}`, clean data: true) antes de seguir para o Deliver.

#### 8. Deliver (LLM)
**Arquivo:** `v1/deliver/system_prompt.txt`
**Nodes:** `Prompt Template-hr0Il` + `GroqModel-v4rce`

**Modelo:** `llama-3.3-70b-versatile` via Groq API
**Temperature:** `0.1`

O Prompt Template monta a entrada com:
- `{user_prompt}` — pergunta original do usuário (vinda do `ChatInput`)
- `{query_result}` — resultado da consulta serializado como texto

**Responsabilidade:** interpretar os dados e responder em linguagem natural, sem mencionar SQL ou detalhes técnicos.

---

## v2 — API REST (LangChain)

Reimplementação do pipeline acima como aplicação Python standalone: um único endpoint Starlette dispara a pipeline completa (planner → validação de intent → SQL builder → executor ClickHouse → deliver) e retorna a resposta final em JSON — sem UI, sem runtime do Langflow.

### Como rodar

```bash
docker compose -f v2/infra.yml up -d   # minio + clickhouse
uv venv
uv pip install -r requirements.txt
uv run python -m v2.start
```

Variáveis de ambiente (lidas de `.env.langchain.local` via `pydantic-settings`, ver `v2/settings.py`):

| Variável             | Obrigatória | Padrão                     | Descrição                          |
|-----------------------|:-----------:|-----------------------------|--------------------------------------|
| `GROQ_API_KEY`         | sim         | —                           | Chave da API Groq                    |
| `CLICKHOUSE_DB_URL`    | sim         | —                           | URL SQLAlchemy do ClickHouse         |
| `GROQ_MODEL`           | não         | `llama-3.3-70b-versatile`  | Modelo usado pelo Planner e Deliver  |
| `GROQ_TEMPERATURE`     | não         | `0.1`                       | Temperature dos dois LLMs            |
| `API_HOST`             | não         | `127.0.0.1`                | Host do uvicorn                      |
| `API_PORT`             | não         | `8000`                      | Porta do uvicorn                     |

### Endpoint

`POST /query` (`v2/start.py`) — body `{"question": "..."}` → `{"question": "...", "answer": "..."}`.
Erros de validação/SQL (`QueryBuilderError`, `ValueError`) retornam `400` com `{"error": "..."}`.

### Pipeline — `v2/pipeline.py` (`AnalyticsPipeline`)

Inicializado uma vez por processo (`__init__` monta catálogo, lê o JSON Schema, constrói as chains do Planner/Deliver e o `JsonToSqlBuilder`); `run(question)` executa por requisição:

1. `planner_chain.invoke({question, json_schema, semantic_catalog})` → string JSON (pode vir com blocos ```` ```json ```` — removidos por `_clean_json`).
2. Se `plan["intent"] == "unknown"` → retorna a mesma mensagem de fallback do v1.
3. Caso contrário: `sql_builder.build(plan)` monta o `Select` do SQLAlchemy; `stmt.compile(compile_kwargs={"literal_binds": True})` gera a SQL como string.
4. `execute_sql(sql, database_url)` executa no ClickHouse via `sqlalchemy` + `pandas`, retorna o resultado serializado como texto (`df.to_string()`, ou `"[]"` se vazio).
5. `deliver_chain.invoke({user_prompt: question, query_result})` → resposta final em linguagem natural.

### Componentes — `v2/components/`

- **`catalog_builder.py`** (`build_semantic_catalog`): equivalente funcional (sem `Component` wrapper) do `v1/components/semantic_catalog_builder_component.py`. Lê `v2/assets/base_semantic_catalog.yaml` + `v2/assets/datasets/abertura_empresas.yaml`, mescla e serializa como YAML.
- **`sql_builder.py`** (`JsonToSqlBuilder`, `QueryBuilderError`): porta 1:1 de `v1/components/sql_query_builder_component.py` — mesmas agregações e operadores de filtro (ver tabela na seção do Planner), sem o wrapper `Component`.
- **`sql_executor.py`** (`execute_sql`): abre conexão via `sqlalchemy.create_engine`, executa `text(sql)`, monta um `DataFrame` com `pandas` e devolve como texto — equivalente ao par `SQLComponent-jrGT7` + `ParserComponent-XHlBw` do v1.

### Planner e Deliver — `v2/planner/chain.py`, `v2/deliver/chain.py`

Cada um é uma chain LCEL: `ChatPromptTemplate.from_messages([("system", system_prompt), ("human", ...)]) | ChatGroq(...) | StrOutputParser()`. `ChatGroq` usa `settings.GROQ_MODEL` / `settings.GROQ_TEMPERATURE` / `settings.GROQ_API_KEY`, `base_url="https://api.groq.com"`.

Os `system_prompt.txt` são praticamente idênticos aos do v1 (`v1/planner/system_prompt.txt`, `v1/deliver/system_prompt.txt`), com uma diferença pontual no Deliver: chaves duplicadas (`{{` `}}`) no exemplo JSON do prompt, exigidas pelo escaping de `ChatPromptTemplate` do LangChain, e uma regra extra explícita ("Responda sempre em português").

**Importante:** como os prompts/catálogo/schema não são compartilhados por import entre `v1/` e `v2/`, uma mudança de regra de negócio (novo campo no catálogo, novo intent, nova regra de prompt) deve ser replicada manualmente nos dois lugares se o objetivo for manter as duas versões em paridade.

---

## Catálogo Semântico

Conteúdo idêntico entre as duas versões, em arquivos separados:

| Conteúdo | v1 | v2 |
|---|---|---|
| Catálogo base | `v1/base_semantic_catalog.yaml` | `v2/assets/base_semantic_catalog.yaml` |
| Dataset | `v1/datasets/abertura_empresas.yaml` | `v2/assets/datasets/abertura_empresas.yaml` |
| JSON Schema do Planner | `v1/planner/planner.schema.json` | `v2/assets/planner_schema.json` |

### Catálogo Base

- Regras globais: limite máximo 1000 registros, intent padrão `aggregation`
- Normalização de UFs (ex.: "São Paulo" → "SP")
- Normalização de datas (ex.: "2024" → `between 202401 e 202412`)
- Validações em runtime: campos, tabelas, métricas, operadores, group_by, order_by

### Dataset: `abertura_empresas`
**Tabela física:** `contabilizei.abertura_empresas_parquet`
**Joins:** não permitidos

| Campo          | Tipo semântico | Agrupável | Filtrável | Notas                        |
|----------------|---------------|-----------|-----------|-------------------------------|
| `cnpj_basico`  | identifier    | não       | sim       | Identificador base da empresa |
| `razao_social` | text          | não       | sim       | Nome jurídico                |
| `uf`           | geography     | sim       | sim       | Normalização UF aplicada     |
| `ano_mes`      | time          | sim       | sim       | Formato YYYYMM, grain: month |

**Conceitos fora do escopo:** ROI, lucro, receita líquida, margem, CAC, LTV, churn, EBITDA, NPS.

---

## Estrutura de Arquivos

```
fiap-discovery-backend/
├── PROBLEM.md                                       # Enunciado do desafio (contexto de negócio)
├── LICENSE.md
├── requirements.txt                                 # Dependências diretas do v2 (pip/uv)
├── pyproject.toml / uv.lock                          # Metadados do projeto Python (v2)
├── .env.langflow.local                              # Variáveis de ambiente do v1 (não versionado)
├── .env.langchain.local                             # Variáveis de ambiente do v2 (não versionado)
├── clickhouse_config/
│   └── init.sql                                    # DDL executado na inicialização do ClickHouse
├── langflow_config/                                 # Estado do Langflow (usado só pelo v1)
│   ├── langflow.db                                  # SQLite com os fluxos Langflow (gerado; não versionado, ver .gitignore)
│   └── secret_key                                  # Chave secreta do Langflow
├── docs/                                             # Diagramas de arquitetura (C4: C2, C3)
│
├── v1/
│   ├── docker-compose.yml                          # Infraestrutura do v1 (MinIO, ClickHouse, Langflow)
│   ├── langflow.dockerfile                         # Imagem customizada do Langflow; importa o fluxo padrão na 1ª subida
│   ├── entrypoint.sh                                # Entrypoint do container langflow (bootstrap do fluxo, ver seção v1)
│   ├── base_semantic_catalog.yaml                  # Catálogo semântico base
│   ├── datasets/
│   │   └── abertura_empresas.yaml                  # Definição do dataset
│   ├── components/
│   │   ├── semantic_catalog_builder_component.py   # Monta catálogo completo (Langflow component)
│   │   ├── validate_intent_component.py            # Valida intent (Langflow component)
│   │   └── sql_query_builder_component.py          # JSON → SQL (Langflow component)
│   ├── planner/
│   │   ├── system_prompt.txt                       # Prompt do Planner LLM
│   │   └── planner.schema.json                     # JSON Schema da saída do Planner
│   ├── deliver/
│   │   └── system_prompt.txt                       # Prompt do Deliver LLM
│   ├── analytics/
│   │   └── abertura_empresas/
│   │       └── abertura_empresas_parquet.py        # Script de preparação dos dados analíticos
│   └── langflow/
│       └── V*.json                                  # Exports versionados do flow (histórico de migrações)
│
├── v2/
│   ├── infra.yml                                    # Infraestrutura do v2 (MinIO + ClickHouse, sem app)
│   ├── start.py                                     # App Starlette; endpoint POST /query; entrypoint (python -m v2.start)
│   ├── pipeline.py                                  # AnalyticsPipeline: orquestra planner → SQL → deliver
│   ├── settings.py                                  # Settings (pydantic-settings), lê .env.langchain.local
│   ├── assets/
│   │   ├── base_semantic_catalog.yaml
│   │   ├── datasets/
│   │   │   └── abertura_empresas.yaml
│   │   └── planner_schema.json
│   ├── components/
│   │   ├── catalog_builder.py                       # build_semantic_catalog (função pura)
│   │   ├── sql_builder.py                           # JsonToSqlBuilder / QueryBuilderError (SQLAlchemy Core)
│   │   └── sql_executor.py                          # execute_sql (ClickHouse → texto via pandas)
│   ├── planner/
│   │   ├── chain.py                                 # build_planner_chain (prompt | ChatGroq | parser)
│   │   └── system_prompt.txt
│   └── deliver/
│       ├── chain.py                                 # build_deliver_chain (prompt | ChatGroq | parser)
│       └── system_prompt.txt
│
├── dados_receita_federal/                          # Dados brutos CNPJ (não versionados)
└── minio_data/                                     # Volume persistente do MinIO (não versionado)
```
