"""
CLI interativo para o assistente analítico Contabilizei (v2 — MCP).

O Deliver LLM atua como agente ReAct com acesso à tool `query_analytics`
exposta pelo servidor MCP (v2/mcp_server.py). O servidor MCP encapsula a
pipeline: planner (LLM) → validação de intent → SQL builder → executor.

Uso:
    python -m v2.main

Variáveis de ambiente obrigatórias (via .env.langchain.local ou ambiente):
    GROQ_API_KEY       — chave da API Groq
    CLICKHOUSE_DB_URL  — URL de conexão ClickHouse
"""

import asyncio
import sys
from pathlib import Path

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from v2.deliver.agent import build_deliver_llm, get_system_prompt
from v2.settings import Settings

_PROJECT_ROOT = str(Path(__file__).parent.parent)


async def main() -> None:
    settings = Settings()
    llm = build_deliver_llm(settings)
    system_prompt = get_system_prompt()

    client = MultiServerMCPClient({
        "contabilizei": {
            "command": sys.executable,
            "args": ["-m", "v2.mcp_server"],
            "transport": "stdio",
            "cwd": _PROJECT_ROOT,
        }
    })

    async with client.session("contabilizei") as session:
        tools = await load_mcp_tools(session)
        agent = create_agent(llm, tools, system_prompt=system_prompt)

        print("Assistente analítico Contabilizei — v2 (MCP)")
        print("Digite sua pergunta ou 'sair' para encerrar.\n")

        while True:
            try:
                question = input("Pergunta: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not question:
                continue
            if question.lower() in ("sair", "exit", "quit"):
                break

            result = await agent.ainvoke({"messages": [("human", question)]})
            print(f"\nResposta: {result['messages'][-1].content}\n")


if __name__ == "__main__":
    asyncio.run(main())
