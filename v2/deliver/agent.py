from pathlib import Path

from langchain_groq import ChatGroq

from v2.settings import Settings

SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.txt"


def build_deliver_llm(settings: Settings) -> ChatGroq:
    """Retorna o ChatGroq configurado para o agente Deliver."""
    return ChatGroq(
        model=settings.GROQ_MODEL,
        temperature=settings.GROQ_TEMPERATURE,
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com",
    )


def get_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
