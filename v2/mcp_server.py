"""
Servidor MCP do assistente analítico Contabilizei.

Expõe a tool `query_analytics` que encapsula a pipeline:
    planner (LLM) → validação de intent → SQL builder → executor (ClickHouse)

Uso standalone (stdio transport):
    python -m v2.mcp_server

O servidor é iniciado automaticamente como subprocesso pelo cliente MCP
definido em v2/main.py.

Variáveis de ambiente obrigatórias (via .env.langchain.local ou ambiente):
    GROQ_API_KEY       — chave da API Groq
    CLICKHOUSE_DB_URL  — URL de conexão ClickHouse
"""

from mcp.server.fastmcp import FastMCP

from v2.pipeline import AnalyticsPipeline
from v2.settings import Settings

_settings = Settings()
_pipeline = AnalyticsPipeline(_settings)

mcp = FastMCP("contabilizei-analytics")


@mcp.tool()
def query_analytics(question: str) -> str:
    """Executa uma consulta analítica sobre dados de abertura de empresas no Brasil.

    Recebe uma pergunta em linguagem natural, planeja a consulta, executa no
    ClickHouse e retorna o resultado tabulado.

    Args:
        question: Pergunta em linguagem natural sobre abertura de empresas.

    Returns:
        Resultado tabulado da consulta analítica.

    Raises:
        ValueError: Se a pergunta estiver fora do escopo dos dados disponíveis.
    """
    return _pipeline.run(question)


if __name__ == "__main__":
    mcp.run()
