import json
import re
from pathlib import Path

from langchain_core.runnables import RunnableBranch, RunnableLambda

from v2.components.catalog_builder import build_semantic_catalog
from v2.components.sql_builder import JsonToSqlBuilder
from v2.components.sql_executor import execute_sql
from v2.deliver.chain import build_deliver_chain
from v2.planner.chain import build_planner_chain
from v2.settings import Settings

ASSETS_DIR = Path(__file__).parent / "assets"
FALLBACK_MESSAGE = (
    "Não foi possível responder à sua pergunta com o conhecimento que tenho no momento. "
    "Tente novamente mais tarde."
)


def _clean_json(text: str) -> str:
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def _parse_plan(query_plan: str) -> dict:
    return json.loads(_clean_json(query_plan))


def create_pipeline(settings: Settings):
    """
    Builds and returns the analytics pipeline as a LangChain Runnable.

    Input:  {"question": str}
    Output: str — natural language answer or fallback message
    """
    semantic_catalog = build_semantic_catalog()
    json_schema = (ASSETS_DIR / "planner_schema.json").read_text(encoding="utf-8")

    planner_chain = build_planner_chain(settings)
    deliver_chain = build_deliver_chain(settings)
    sql_builder = JsonToSqlBuilder(database_url=settings.CLICKHOUSE_DB_URL)

    def run_planner(state: dict) -> dict:
        query_plan = planner_chain.invoke({
            "question": state["question"],
            "json_schema": json_schema,
            "semantic_catalog": semantic_catalog,
        })
        return {**state, "query_plan": query_plan}

    def is_unknown_intent(state: dict) -> bool:
        return _parse_plan(state["query_plan"]).get("intent") == "unknown"

    def build_and_execute_sql(state: dict) -> dict:
        plan = _parse_plan(state["query_plan"])
        stmt = sql_builder.build(plan)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        query_result = execute_sql(sql, settings.CLICKHOUSE_DB_URL)
        return {**state, "query_result": query_result}

    def run_deliver(state: dict) -> str:
        return deliver_chain.invoke({
            "user_prompt": state["question"],
            "query_result": state["query_result"],
        })

    known_path = RunnableLambda(build_and_execute_sql) | RunnableLambda(run_deliver)

    return RunnableLambda(run_planner) | RunnableBranch(
        (is_unknown_intent, RunnableLambda(lambda _: FALLBACK_MESSAGE)),
        known_path,
    )
