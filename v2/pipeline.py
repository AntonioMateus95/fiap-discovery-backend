import json
import re
from pathlib import Path

from v2.components.catalog_builder import build_semantic_catalog
from v2.components.sql_builder import JsonToSqlBuilder
from v2.components.sql_executor import execute_sql
from v2.planner.chain import build_planner_chain
from v2.settings import Settings

ASSETS_DIR = Path(__file__).parent / "assets"


def _clean_json(text: str) -> str:
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


class AnalyticsPipeline:
    """Planner → intent check → SQL builder → SQL executor.

    Inicializado uma vez; reutilizado em cada chamada de ferramenta.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.semantic_catalog = build_semantic_catalog()
        self.json_schema = (ASSETS_DIR / "planner_schema.json").read_text(encoding="utf-8")
        self.planner_chain = build_planner_chain(settings)
        self.sql_builder = JsonToSqlBuilder(database_url=settings.CLICKHOUSE_DB_URL)

    def run(self, question: str) -> str:
        """Executa o pipeline e retorna o resultado tabulado.

        Raises:
            ValueError: Se a intent for 'unknown' (pergunta fora do escopo).
        """
        query_plan_str = self.planner_chain.invoke({
            "question": question,
            "json_schema": self.json_schema,
            "semantic_catalog": self.semantic_catalog,
        })

        plan = json.loads(_clean_json(query_plan_str))

        if plan.get("intent") == "unknown":
            raise ValueError(
                "A pergunta está fora do escopo analítico. "
                "Só é possível responder sobre dados de abertura de empresas no Brasil."
            )

        stmt = self.sql_builder.build(plan)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        return execute_sql(sql, self.settings.CLICKHOUSE_DB_URL)
