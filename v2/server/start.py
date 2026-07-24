"""
Servidor MCP do assistente analítico Contabilizei.

Expõe a tool `query_analytics` que encapsula a pipeline:
    planner (LLM) → validação de intent → SQL builder → executor (ClickHouse)

Uso standalone (streamable-http transport):
    python -m v2.server.start

O servidor escuta em MCP_SERVER_HOST:MCP_SERVER_PORT (padrão 127.0.0.1:8000)
no endpoint /mcp e é consumido pelo cliente MCP definido em v2/main.py.

Variáveis de ambiente obrigatórias (via .env.langchain.local ou ambiente):
    GROQ_API_KEY       — chave da API Groq
    CLICKHOUSE_DB_URL  — URL de conexão ClickHouse
"""

from mcp.server.fastmcp import FastMCP

from v2.server.pipeline import AnalyticsPipeline
from v2.server.settings import Settings

_settings = Settings()
_pipeline = AnalyticsPipeline(_settings)

mcp = FastMCP(
    "contabilizei-analytics",
    host=_settings.MCP_SERVER_HOST,
    port=_settings.MCP_SERVER_PORT,
)


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
    mcp.run(transport="streamable-http")
