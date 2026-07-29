"""
API REST do assistente analítico Contabilizei (v2).

Um único endpoint dispara a pipeline completa — planner (LLM) → validação de
intent → SQL builder → executor (ClickHouse) → deliver (LLM) — e retorna a
resposta final em JSON.

Uso:
    python -m v2.start

Variáveis de ambiente obrigatórias (via .env.langchain.local ou ambiente):
    GROQ_API_KEY       — chave da API Groq
    CLICKHOUSE_DB_URL  — URL de conexão ClickHouse

Variáveis opcionais:
    API_HOST           — host da API (padrão 127.0.0.1)
    API_PORT           — porta da API (padrão 8000)
"""

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from v2.components.sql_builder import QueryBuilderError
from v2.pipeline import AnalyticsPipeline
from v2.settings import Settings

_settings = Settings()
_pipeline = AnalyticsPipeline(_settings)


async def query_analytics(request: Request) -> JSONResponse:
    body = await request.json()
    question = (body.get("question") or "").strip()

    if not question:
        return JSONResponse({"error": "Campo 'question' é obrigatório."}, status_code=400)

    try:
        answer = _pipeline.run(question)
    except (QueryBuilderError, ValueError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    return JSONResponse({"question": question, "answer": answer})


app = Starlette(routes=[
    Route("/query", query_analytics, methods=["POST"]),
])


if __name__ == "__main__":
    uvicorn.run(app, host=_settings.API_HOST, port=_settings.API_PORT)
