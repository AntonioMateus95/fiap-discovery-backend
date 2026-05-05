# Contabilizei — Analytics Assistant

Aplicação de analytics conversacional construída sobre [Langflow](https://www.langflow.org/). O usuário faz uma pergunta em linguagem natural; um pipeline de componentes a transforma em uma consulta SQL executada no ClickHouse e devolve uma resposta textual.

---

## Arquitetura

```
[Usuário] → [Langflow :7860] → [ClickHouse :8123] → [MinIO :9000]
```

| Serviço      | Porta(s)              | Função                                       |
|--------------|-----------------------|----------------------------------------------|
| MinIO        | 9000 (API), 9001 (UI) | Object storage: dados analíticos e arquivos do Langflow |
| ClickHouse   | 8123 (HTTP), 9002 (TCP) | Banco de dados analítico                   |
| Langflow     | 7860                  | Orquestrador do pipeline (UI + runtime)      |

O fluxo converte a pergunta em um JSON estruturado via LLM (Groq `llama-3.3-70b-versatile`), traduz esse JSON para SQL com SQLAlchemy e executa a query diretamente no ClickHouse. O resultado é interpretado por um segundo LLM e devolvido ao usuário em linguagem natural.

---

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/)
- Chave de API do [Groq](https://console.groq.com/)

---

## Configuração

### 1. Variáveis de ambiente

Crie o arquivo `.env.langflow.local` na raiz do projeto com a sua chave Groq:

```
GROQ_API_KEY=<sua-chave-groq>
```

### 2. MinIO — buckets e dados

Após subir os serviços (passo 3), acesse o console MinIO em **http://localhost:9001** (usuário: `admin`, senha: `password123`) e crie dois buckets:

| Bucket         | Finalidade                                      |
|----------------|-------------------------------------------------|
| `contabilizei` | Dados analíticos lidos pelo ClickHouse via S3   |
| `langflow`     | Armazenamento de arquivos internos do Langflow  |

No bucket **`contabilizei`**, carregue o arquivo parquet no seguinte caminho:

```
analytics/abertura_empresas/<arquivo>.parquet
```

O arquivo parquet pode ser encontrado no seguinte [link](https://drive.google.com/file/d/1drPIZt2nU0fcInHU1TJwAO5oN_1hkRhy/view?usp=sharing).

O ClickHouse lê esse arquivo diretamente via S3 Engine, sem necessidade de importação manual.

### 3. Subir os serviços

```bash
docker compose up -d
```

Aguarde todos os contêineres ficarem saudáveis antes de prosseguir.

---

## Uso

Acesse o Langflow em **http://localhost:7860** e abra o flow **Contabilizei**.

Exemplos de perguntas:

- *Quantas empresas foram abertas em 2024?*
- *Quais estados tiveram mais aberturas em 2024?*
- *Como evoluíram as aberturas de empresas ao longo de 2024?*

---

## Pipeline

O fluxo possui dois caminhos dependendo do resultado do Planner:

```
[Schema JSON] ──────────────────────────────────────────────────────────┐
                                                                         ▼
[Catálogo semântico base] ──► [Montagem do catálogo] ──► [Parser] ──► [Prompt Template (Planner)]
[abertura_empresas.yaml] ────────────────────────────────────────────►  │
                                                                         │ system_message
[Chat Input] ───────────────────────────────────────────────────────►   │
                                                                         ▼
                                                                 [Groq LLM — Planner]
                                                                 llama-3.3-70b-versatile
                                                                         │
                                                                         ▼
                                                                 [Validar intent]
                                                                 intent == "unknown"?
                                          ┌──────── true ────────────── ┤
                                          ▼                              │ false
                               [Text Operations]                         ▼
                               (mensagem de fallback)           [SQL Query Builder]
                                          │                      JSON → SQL (SQLAlchemy)
                                          ▼                              │
                               [Chat Output ①]                           ▼
                               (intent desconhecido)            [SQL Database]
                                                                 Executa no ClickHouse
                                                                         │
                                                                         ▼
                                                                 [Parser: DataFrame → texto]
                                                                         │
                                                                         ▼
                                                                 [Prompt Template (Deliver)]
                                                                         │
                                                                         ▼
                                                                 [Groq LLM — Deliver]
                                                                 llama-3.3-70b-versatile
                                                                         │
                                                                         ▼
                                                                 [Chat Output ②]
                                                                 (resposta final)
```

---

## Estrutura de Arquivos

```
contabilizei/
├── docker-compose.yml                              # Infraestrutura (MinIO, ClickHouse, Langflow)
├── langflow.dockerfile                             # Imagem customizada do Langflow
├── .env.langflow.local                             # Variáveis de ambiente locais (não versionado)
├── clickhouse_config/
│   └── init.sql                                    # DDL executado na inicialização do ClickHouse
├── langflow_config/
│   ├── langflow.db                                 # SQLite com os fluxos Langflow
│   └── secret_key                                  # Chave secreta do Langflow
├── v1/
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
│   └── langflow/
│       └── V202604302236__melhorias_nos_componentes_customizados.json  # Export do flow
├── dados_receita_federal/                          # Dados brutos CNPJ (não versionados)
└── minio_data/                                     # Volume persistente do MinIO
```

---

## Referências

- [Langflow — Documentação](https://docs.langflow.org/)
- [ClickHouse S3 Engine](https://clickhouse.com/docs/en/engines/table-engines/integrations/s3)
- [Groq API](https://console.groq.com/docs/openai)
- [Dados Abertos CNPJ — Receita Federal](https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj)
