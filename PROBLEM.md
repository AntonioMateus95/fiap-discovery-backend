# Desafio FIAP MBA Discovery 2025 — Contabilizei

## Contexto

A Contabilizei é o maior escritório de contabilidade do Brasil, fundada em 2013, com mais de 70 mil clientes, 1.500 colaboradores e 12 anos de experiência. A empresa é baseada em dados e consolida informações de diversas fontes em seu data lake. O time de dados constrói pipelines de ingestão e tabelas processadas que respondem problemas de negócio — mas o acesso a esses dados ainda depende de profissionais técnicos.

## Problema

> **Como utilizar inteligência artificial para democratizar o acesso e a interpretação de dados empresariais, permitindo que usuários internos, sem conhecimento técnico em SQL, Python ou Dashboards, possam tomar decisões baseadas em dados com facilidade, segurança e autonomia?**

As áreas de negócio precisam de autonomia para realizar consultas, análises e criação de gráficos de forma fácil e intuitiva, sem depender do time de dados para cada solicitação.

## Objetivo do Projeto

Desenvolver uma **prototipação funcional** de uma solução que utilize IA para permitir que usuários não técnicos consigam:

- Fazer perguntas em linguagem natural (português);
- Obter respostas acionáveis a partir dos dados (visuais, resumos ou insights automáticos);
- Reduzir a dependência de times técnicos para consultas e relatórios simples.

**Diferencial esperado:** criar gráficos ou dashboards de maneira fácil e intuitiva.

## Requisitos da Solução

### 1. Interface Amigável
- Chatbot, dashboard com IA embarcada, ou assistente conversacional.
- Consultas em linguagem natural.

### 2. Interpretação Inteligente
- IA (NLP, LLMs ou SLMs) para traduzir perguntas em linguagem natural.
- Saídas: resumos em texto, visualizações automáticas (gráficos, tabelas, explicações).
- Base de dados da Receita Federal como referência.

### 3. Governança e Segurança
- Aspectos de segurança e privacidade dos dados.
- Restrições baseadas em perfil de usuário (controle de acesso por papel).

### 4. Aplicabilidade Real
- Contextualizado na área de **Branding** da Contabilizei.

## Fonte de Dados

Dados abertos da Receita Federal sobre empresas (CNPJs).

**Por que usar a base da Receita Federal?**
- Fonte oficial e completa: ~23 milhões de CNPJs cadastrados.
- Permite comparações YoY, QoQ, MoM por porte, cidade ou setor.
- Releases mensais com estatísticas exclusivas.
- Dados públicos — sem barreiras de licenciamento.

**Valor para Branding:**
- Thought-leadership: análises exclusivas citadas pela imprensa.
- Narrativas de crescimento (ex.: "Interior cresce 18% YoY").
- Calendário editorial previsível (atualização mensal).

## Entregáveis Esperados

1. Protótipo ou apresentação conceitual funcional da solução.
2. Justificativa técnica e estratégica da abordagem escolhida.
3. Demonstração de como a solução democratiza o acesso a dados.
4. Documento com descrição do projeto: objetivos, escopo, público-alvo e justificativa.
5. Diagrama da arquitetura proposta.
6. Considerações sobre impactos e desafios (éticos, técnicos e organizacionais).

## Exemplos de Soluções Possíveis

| Tipo | Descrição |
|------|-----------|
| **Chatbot de Dados** | Assistente conversacional que responde perguntas como "Quantas empresas foram abertas em SP no último trimestre?" |
| **Painel com IA** | Dashboard que sugere insights automáticos baseados em tendências dos dados |
| **Sistema de Q&A** | Interface que interpreta perguntas e apresenta resultados como gráficos ou texto explicativo |

## Tecnologias Sugeridas (não obrigatórias)

- Modelos de linguagem natural: GPT, BERT, Llama, etc.
- Ferramentas open source: Streamlit, LangChain, LlamaIndex
- APIs de LLMs: OpenAI, Cohere, Google, Groq, etc.
- Agentes de IA

## Mentores

- **Fabio Jardim** — Head de Dados na Contabilizei (ex-Casas Bahia, OLX, Dock)
- **Diogenes Braz de Souza** — Coordenador de Engenharia de Dados na Contabilizei
