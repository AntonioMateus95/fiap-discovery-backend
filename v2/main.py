"""
CLI interativo para o assistente analítico Contabilizei (v2 — LangChain).

Uso:
    python -m v2.main

Variáveis de ambiente obrigatórias (via .env ou ambiente):
    GROQ_API_KEY       — chave da API Groq
    CLICKHOUSE_DB_URL  — URL de conexão ClickHouse
                         ex: clickhouse+http://admin:password123@localhost:8123/contabilizei
"""

from v2.pipeline import create_pipeline
from v2.settings import Settings


def main() -> None:
    settings = Settings()
    pipeline = create_pipeline(settings)

    print("Assistente analítico Contabilizei — v2 (LangChain)")
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

        response = pipeline.invoke({"question": question})
        print(f"\nResposta: {response}\n")


if __name__ == "__main__":
    main()
