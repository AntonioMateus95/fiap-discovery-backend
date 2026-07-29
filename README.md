# Contabilizei — Analytics Assistant

Aplicação de analytics conversacional. O usuário faz uma pergunta em linguagem natural; um pipeline a transforma em uma consulta SQL executada no ClickHouse e devolve uma resposta textual.

O repositório contém **duas implementações** do mesmo pipeline, lado a lado:

| Versão | Orquestração | Interface | Pasta |
|--------|--------------|-----------|-------|
| **v1** | [Langflow](https://www.langflow.org/) (fluxo visual de componentes) | UI do Langflow (chat embutido) | [`v1/`](v1/) |
| **v2** | [LangChain](https://python.langchain.com/) + [Starlette](https://www.starlette.io/) (código Python puro) | API REST (`POST /query`) | [`v2/`](v2/) |

Ambas compartilham o mesmo catálogo semântico, os mesmos prompts de LLM e a mesma infraestrutura de dados (MinIO + ClickHouse) — a diferença é a camada de orquestração: v1 roda os componentes dentro do runtime visual do Langflow, v2 os reimplementa como um pipeline Python direto, exposto via API.

Contexto do desafio (FIAP MBA Discovery — Contabilizei): ver [`PROBLEM.md`](PROBLEM.md).

---

## Arquitetura

```
[Usuário] → [v1: Langflow :7860]  ─┐
            [v2: API REST :8000]  ─┴─► [ClickHouse :8123] → [MinIO :9000]
```

| Serviço      | Porta(s)                | Usado por | Função                                                  |
|--------------|--------------------------|-----------|-----------------------------------------------------------|
| MinIO        | 9000 (API), 9001 (UI)    | v1, v2    | Object storage: dados analíticos (e arquivos do Langflow em v1) |
| ClickHouse   | 8123 (HTTP), 9002 (TCP)  | v1, v2    | Banco de dados analítico                                |
| Langflow     | 7860                     | v1        | Orquestrador visual do pipeline (UI + runtime)          |
| API REST     | 8000                     | v2        | Orquestrador do pipeline em Python (Starlette + uvicorn) |

O fluxo converte a pergunta em um JSON estruturado via LLM (Groq `llama-3.3-70b-versatile`), traduz esse JSON para SQL com SQLAlchemy e executa a query diretamente no ClickHouse. O resultado é interpretado por um segundo LLM e devolvido ao usuário em linguagem natural. Veja o detalhamento do pipeline mais abaixo.

---

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/) — infraestrutura (MinIO, ClickHouse, e o Langflow no caso do v1)
- Chave de API do [Groq](https://console.groq.com/)
- Para rodar o v2 localmente (fora de container): Python 3.12 e [uv](https://docs.astral.sh/uv/)

---

## Configuração comum (MinIO + ClickHouse)

Os dois caminhos (v1 e v2) dependem dos mesmos dados no MinIO/ClickHouse.

### 1. Buckets e dados no MinIO

Depois de subir os serviços (passo específico de cada versão abaixo), acesse o console MinIO em **http://localhost:9001** (usuário: `admin`, senha: `password123`) e crie o bucket:

| Bucket         | Finalidade                                    |
|----------------|------------------------------------------------|
| `contabilizei` | Dados analíticos lidos pelo ClickHouse via S3   |
| `langflow`     | Uploads de arquivos feitos dentro do langflow   |

No bucket **`contabilizei`**, carregue o arquivo parquet no seguinte caminho:

```
analytics/abertura_empresas/<arquivo>.parquet
```

O arquivo parquet pode ser encontrado neste [link](https://drive.google.com/file/d/1drPIZt2nU0fcInHU1TJwAO5oN_1hkRhy/view?usp=sharing).

O ClickHouse lê esse arquivo diretamente via `S3 Engine` (definido em `clickhouse_config/init.sql`), sem necessidade de importação manual.

---

## v1 — Langflow

### Configuração

Crie o arquivo `.env.langflow.local` na raiz do projeto:

```
GROQ_API_KEY=<sua-chave-groq>
```

No console MinIO, crie também o bucket `langflow` (armazenamento interno de arquivos do Langflow), além do bucket `contabilizei` da seção anterior.

### Subir os serviços

```bash
docker compose -f v1/docker-compose.yml up -d
```

Aguarde todos os contêineres ficarem saudáveis.

### Uso

Acesse o Langflow em **http://localhost:7860** e abra o flow **Contabilizei**.

Exemplos de perguntas:

- *Quantas empresas foram abertas em 2024?*
- *Quais estados tiveram mais aberturas em 2024?*
- *Como evoluíram as aberturas de empresas ao longo de 2024?*

---

## v2 — API REST (LangChain)

### Configuração

Crie o arquivo `.env.langchain.local` na raiz do projeto:

```
GROQ_API_KEY=<sua-chave-groq>
CLICKHOUSE_DB_URL=clickhouse+http://admin:password123@localhost:8123/contabilizei
```

### Subir a infraestrutura (MinIO + ClickHouse)

```bash
docker compose -f v2/infra.yml up -d
```

O v2 não tem contêiner próprio: a API roda localmente e se conecta ao ClickHouse exposto pelo compose acima.

### Instalar dependências e rodar a API

```bash
uv venv
uv pip install -r requirements.txt
uv run python -m v2.start
```

A API sobe em `http://127.0.0.1:8000` (configurável via `API_HOST`/`API_PORT`).

### Uso

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Quantas empresas foram abertas em 2024?"}'
```

Resposta:

```json
{
  "question": "Quantas empresas foram abertas em 2024?",
  "answer": "..."
}
```

Se o Planner classificar a pergunta como fora do catálogo semântico (`intent: unknown`), a API responde com a mensagem de fallback padrão em vez de erro.

---

## Pipeline

O pipeline lógico é o mesmo nas duas versões — o que muda é apenas quem executa cada etapa (nó do Langflow em v1, função/chain Python em v2):

```
[Schema JSON] ──────────────────────────────────────────────────────────┐
                                                                         ▼
[Catálogo semântico base] ──► [Montagem do catálogo] ──► [Prompt (Planner)]
[abertura_empresas.yaml] ────────────────────────────────────────────►  │
                                                                         │ system_message
[Pergunta do usuário] ────────────────────────────────────────────────► │
                                                                         ▼
                                                                 [Groq LLM — Planner]
                                                                 llama-3.3-70b-versatile
                                                                         │
                                                                         ▼
                                                                 [Validar intent]
                                                                 intent == "unknown"?
                                          ┌──────── true ────────────── ┤
                                          ▼                              │ false
                               [mensagem de fallback]                    ▼
                                          │                      [SQL Query Builder]
                                          │                      JSON → SQL (SQLAlchemy)
                                          │                              │
                                          │                              ▼
                                          │                      [Executa no ClickHouse]
                                          │                              │
                                          │                              ▼
                                          │                      [Prompt (Deliver)]
                                          │                      {user_prompt} + {query_result}
                                          │                              │
                                          │                              ▼
                                          │                      [Groq LLM — Deliver]
                                          │                      llama-3.3-70b-versatile
                                          │                              │
                                          ▼                              ▼
                                              [Resposta final ao usuário]
```

- **v1**: cada caixa acima é um nó do flow **Contabilizei**, armazenado em `langflow_config/langflow.db` (flow id `1105129f-452c-4730-979b-34373d655a0b`). Componentes customizados ficam em `v1/components/*.py` (subclasses de `Component`, executadas pelo runtime do Langflow).
- **v2**: o mesmo pipeline é orquestrado por `v2/pipeline.py` (`AnalyticsPipeline.run`), chamado pelo endpoint `POST /query` (`v2/start.py`). Planner e Deliver são chains LCEL (`prompt | ChatGroq | StrOutputParser`) em `v2/planner/chain.py` e `v2/deliver/chain.py`; o SQL Query Builder e o executor são classes/funções puras em `v2/components/`.

### Catálogo semântico

Compartilhado pelas duas versões — mesmo conteúdo, arquivos diferentes:

- **v1**: `v1/base_semantic_catalog.yaml` + `v1/datasets/abertura_empresas.yaml`
- **v2**: `v2/assets/base_semantic_catalog.yaml` + `v2/assets/datasets/abertura_empresas.yaml`

**Dataset `abertura_empresas`** — tabela física `contabilizei.abertura_empresas_parquet`, sem joins:

| Campo          | Tipo semântico | Agrupável | Filtrável | Notas                        |
|----------------|---------------|-----------|-----------|-------------------------------|
| `cnpj_basico`  | identifier    | não       | sim       | Identificador base da empresa |
| `razao_social` | text          | não       | sim       | Nome jurídico                 |
| `uf`           | geography     | sim       | sim       | Normalização UF aplicada      |
| `ano_mes`      | time          | sim       | sim       | Formato `YYYYMM`, grain: month |

**Conceitos fora do escopo:** ROI, lucro, receita líquida, margem, CAC, LTV, churn, EBITDA, NPS — perguntas sobre esses termos retornam `intent: unknown`.

---

## Estrutura de Arquivos

```
fiap-discovery-backend/
├── PROBLEM.md                                       # Enunciado do desafio (contexto de negócio)
├── LICENSE.md
├── clickhouse_config/
│   └── init.sql                                     # DDL executado na inicialização do ClickHouse (S3 Engine)
├── langflow_config/                                 # Estado do Langflow (usado só pelo v1)
│   ├── langflow.db                                  # SQLite com os fluxos Langflow
│   └── secret_key                                   # Chave secreta do Langflow
├── docs/                                             # Diagramas de arquitetura (C4)
│   ├── C2.plantuml
│   └── C3.plantuml / C3.drawio
├── requirements.txt                                 # Dependências diretas do v2 (pip/uv)
├── pyproject.toml / uv.lock                          # Metadados do projeto Python (v2)
│
├── v1/                                                # ── Versão Langflow ──
│   ├── docker-compose.yml                            # MinIO + ClickHouse + Langflow
│   ├── langflow.dockerfile                            # Imagem customizada do Langflow
│   ├── base_semantic_catalog.yaml                     # Catálogo semântico base
│   ├── datasets/
│   │   └── abertura_empresas.yaml                     # Definição do dataset
│   ├── components/
│   │   ├── semantic_catalog_builder_component.py      # Monta catálogo completo (Langflow component)
│   │   ├── validate_intent_component.py                # Valida intent (Langflow component)
│   │   └── sql_query_builder_component.py              # JSON → SQL (Langflow component)
│   ├── planner/
│   │   ├── system_prompt.txt                          # Prompt do Planner LLM
│   │   └── planner.schema.json                         # JSON Schema da saída do Planner
│   ├── deliver/
│   │   └── system_prompt.txt                          # Prompt do Deliver LLM
│   ├── analytics/abertura_empresas/
│   │   └── abertura_empresas_parquet.py                # Script de preparação dos dados analíticos
│   └── langflow/*.json                                 # Exports versionados do flow
│
└── v2/                                                # ── Versão API REST (LangChain) ──
    ├── infra.yml                                       # MinIO + ClickHouse (sem contêiner de app)
    ├── start.py                                         # App Starlette; endpoint POST /query
    ├── pipeline.py                                      # AnalyticsPipeline: orquestra planner → SQL → deliver
    ├── settings.py                                      # Settings (pydantic-settings), lê .env.langchain.local
    ├── assets/
    │   ├── base_semantic_catalog.yaml
    │   ├── datasets/abertura_empresas.yaml
    │   └── planner_schema.json
    ├── components/
    │   ├── catalog_builder.py                           # Monta catálogo completo (função pura)
    │   ├── sql_builder.py                                # JsonToSqlBuilder: JSON → SQL (SQLAlchemy Core)
    │   └── sql_executor.py                               # Executa SQL no ClickHouse, retorna texto (pandas)
    ├── planner/
    │   ├── chain.py                                      # build_planner_chain: prompt | ChatGroq | parser
    │   └── system_prompt.txt
    └── deliver/
        ├── chain.py                                      # build_deliver_chain: prompt | ChatGroq | parser
        └── system_prompt.txt
```

*(Diretórios não versionados: `dados_receita_federal/`, `minio_data/`, `.venv/`.)*

---

## Referências

- [Langflow — Documentação](https://docs.langflow.org/)
- [LangChain — Documentação](https://python.langchain.com/)
- [ClickHouse S3 Engine](https://clickhouse.com/docs/en/engines/table-engines/integrations/s3)
- [Groq API](https://console.groq.com/docs/openai)
- [Dados Abertos CNPJ — Receita Federal](https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj)
