# Contabilizei — Analytics Assistant (Langflow)

## Visão Geral

Aplicação de analytics conversacional construída sobre Langflow. O usuário faz uma pergunta em linguagem natural; um pipeline de componentes a transforma em uma consulta SQL executada no ClickHouse e devolve uma resposta textual.

O fluxo visual está armazenado em `langflow_config/langflow.db` (flow id: `1105129f-452c-4730-979b-34373d655a0b`, nome: **Contabilizei**).

---

## Infraestrutura (`docker-compose.yml`)

| Serviço      | Imagem                              | Porta(s)              | Função                                  |
|--------------|-------------------------------------|-----------------------|-----------------------------------------|
| `minio`      | `minio/minio`                       | 9000, 9001            | Object storage (dados raw CNPJ/Receita) |
| `clickhouse` | `clickhouse/clickhouse-server`      | 8123 (HTTP), 9002 (TCP) | Banco de dados analítico              |
| `langflow`   | `langflow.dockerfile` (customizado) | 7860                  | Orquestrador do pipeline (UI + runtime) |

Credenciais padrão: `admin` / `password123`. Banco ClickHouse: `contabilizei`.

---

## Pipeline — Fluxo de Dados

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

---

## Nós do Fluxo Langflow

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
| `SQLComponent-jrGT7`          | SQL Database                         | SQLComponent           | (3617, 391)     |
| `ParserComponent-XHlBw`       | Parser (DataFrame → texto)           | ParserComponent        | (4005, 543)     |
| `Prompt Template-hr0Il`       | Prompt Template (Deliver)            | Prompt Template        | (4476, 239)     |
| `GroqModel-v4rce`             | Groq — Deliver                       | GroqModel              | (4970, 258)     |
| `ChatOutput-9Npsa`            | Chat Output ② (resposta final)      | ChatOutput             | (5489, 491)     |

---

## Arestas do Fluxo (Conexões)

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

---

## Componentes Detalhados

### 1. Inputs estáticos

- **`TextInput-AYh8e` — Schema json para o planner**: contém o JSON Schema completo (`planner.schema.json`) injetado como variável `{json_schema}` no prompt do Planner.
- **`TextInput-cl2BX` — Catálogo semântico genérico**: contém o conteúdo de `v1/base_semantic_catalog.yaml`.
- **`File-hMTWH` — Read File**: lê o arquivo `abertura_empresas` (YAML do dataset) do storage local e passa o caminho para o componente de montagem do catálogo.

---

### 2. Montagem do Catálogo Semântico
**Arquivo:** `v1/components/semantic_catalog_builder_component.py`  
**Node:** `PythonREPLComponent-pJ2PO`

Mescla o catálogo base (`base_semantic_catalog.yaml`) com o dataset YAML lido pelo `File-hMTWH`, populando a chave `datasets` no YAML final. O resultado é passado para um `Parser` que o serializa como texto puro antes de entrar no Prompt Template.

---

### 3. Planner (LLM)
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

**Estrutura do JSON de saída** (`planner.schema.json`):

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
Operadores de filtro: `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `in`, `between`.

---

### 4. Validar Intent
**Arquivo:** `v1/components/validate_intent_component.py`  
**Node:** `PythonREPLComponent-1s7YW`

Roteador condicional. Verifica se `intent == "unknown"` no JSON do Planner.

- **`true_result`** (intent desconhecido) → `TextOperations-RpUyu` → `ChatOutput-Vk7t0`
- **`false_result`** (intent reconhecido) → `PythonREPLComponent-Mwems` (SQL Query Builder)

---

### 5. Fallback (intent unknown)
**Node:** `TextOperations-RpUyu`

Usa substituição via regex (`^.+$`) para substituir qualquer texto pela mensagem fixa de fallback:

> *"Não foi possível responder à sua pergunta com o conhecimento que tenho no momento. Tente novamente mais tarde."*

A saída vai para `ChatOutput-Vk7t0` encerrando o fluxo.

---

### 6. SQL Query Builder
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

---

### 7. Execução no ClickHouse
**Node:** `SQLComponent-jrGT7`

Executa o SQL gerado pelo Query Builder diretamente no ClickHouse. A tabela analítica principal é:

```
contabilizei.abertura_empresas_parquet
```

O resultado é um `DataFrame` que passa por um `Parser` (modo Stringify, template `{sql}`, clean data: true) antes de seguir para o Deliver.

---

### 8. Deliver (LLM)
**Arquivo:** `v1/deliver/system_prompt.txt`  
**Nodes:** `Prompt Template-hr0Il` + `GroqModel-v4rce`

**Modelo:** `llama-3.3-70b-versatile` via Groq API  
**Temperature:** `0.1`

O Prompt Template monta a entrada com:
- `{user_prompt}` — pergunta original do usuário (vinda do `ChatInput`)
- `{query_result}` — resultado da consulta serializado como texto

**Responsabilidade:** interpretar os dados e responder em linguagem natural, sem mencionar SQL ou detalhes técnicos.

---

## Catálogo Semântico

### Catálogo Base — `v1/base_semantic_catalog.yaml`

- Regras globais: limite máximo 1000 registros, intent padrão `aggregation`
- Normalização de UFs (ex.: "São Paulo" → "SP")
- Normalização de datas (ex.: "2024" → `between 202401 e 202412`)
- Validações em runtime: campos, tabelas, métricas, operadores, group_by, order_by

### Dataset: `abertura_empresas`
**Arquivo:** `v1/datasets/abertura_empresas.yaml`  
**Tabela física:** `contabilizei.abertura_empresas_parquet`  
**Joins:** não permitidos

| Campo          | Tipo semântico | Agrupável | Filtrável | Notas                        |
|----------------|---------------|-----------|-----------|------------------------------|
| `cnpj_basico`  | identifier    | não       | sim       | Identificador base da empresa |
| `razao_social` | text          | não       | sim       | Nome jurídico                |
| `uf`           | geography     | sim       | sim       | Normalização UF aplicada     |
| `ano_mes`      | time          | sim       | sim       | Formato YYYYMM, grain: month |

**Conceitos fora do escopo:** ROI, lucro, receita líquida, margem, CAC, LTV, churn, EBITDA, NPS.

---

## Estrutura de Arquivos

```
contabilizei/
├── docker-compose.yml                              # Infraestrutura (MinIO, ClickHouse, Langflow)
├── langflow.dockerfile                             # Imagem customizada do Langflow
├── clickhouse_config/
│   └── init.sql                                    # DDL executado na inicialização do ClickHouse
├── langflow_config/
│   ├── langflow.db                                 # SQLite com os fluxos Langflow
│   └── secret_key                                  # Chave secreta do Langflow
├── v1/
│   ├── base_semantic_catalog.yaml                  # Catálogo semântico base
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
│   ├── langflow/
│   │   └── V202604302236__melhorias_nos_componentes_customizados.json  # Export do flow
│   └── datasets/
│       └── abertura_empresas.yaml                  # Definição do dataset
├── dados_receita_federal/                          # Dados brutos CNPJ (não versionados)
└── minio_data/                                     # Volume persistente do MinIO
```
