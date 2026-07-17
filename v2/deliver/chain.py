from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.txt"


def build_deliver_chain(settings):
    """Returns a Runnable that accepts {user_prompt, query_result}."""
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Pergunta do usuário:\n{user_prompt}\n\nResultado da consulta:\n{query_result}"),
    ])

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        temperature=settings.GROQ_TEMPERATURE,
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com",
    )

    return prompt | llm | StrOutputParser()
