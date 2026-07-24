from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.txt"


def build_planner_chain(settings):
    """Returns a Runnable that accepts {question, json_schema, semantic_catalog}."""
    system_template = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("human", "{question}"),
    ])

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        temperature=settings.GROQ_TEMPERATURE,
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com",
    )

    return prompt | llm | StrOutputParser()
