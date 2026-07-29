from typing import Any

from sqlalchemy import MetaData, Table, and_, asc, desc, func, select
from sqlalchemy import create_engine
from sqlalchemy.sql import Select


class QueryBuilderError(Exception):
    pass


class JsonToSqlBuilder:
    def __init__(self, database_url: str, metadata: MetaData | None = None):
        self.engine = create_engine(database_url)
        self.metadata = metadata or MetaData()

    def build(self, spec: dict[str, Any]) -> Select:
        table_name = spec.get("table")
        if not table_name:
            raise QueryBuilderError("Campo 'table' é obrigatório.")

        tbl = self._load_table(table_name)

        select_exprs = self._build_select(tbl, spec.get("select", []))
        stmt = select(*select_exprs)

        filters = spec.get("filters", [])
        if filters:
            stmt = stmt.where(and_(*self._build_filters(tbl, filters)))

        group_by_fields = spec.get("group_by", [])
        if group_by_fields:
            stmt = stmt.group_by(*[self._get_column(tbl, f) for f in group_by_fields])

        order_by_items = spec.get("order_by", [])
        if order_by_items:
            stmt = stmt.order_by(*self._build_order_by(order_by_items))

        limit_value = spec.get("limit")
        if limit_value is not None:
            if not isinstance(limit_value, int) or limit_value <= 0:
                raise QueryBuilderError("Campo 'limit' deve ser inteiro positivo.")
            stmt = stmt.limit(limit_value)

        return stmt

    def _load_table(self, table_name: str) -> Table:
        return Table(table_name, self.metadata, autoload_with=self.engine)

    def _build_select(self, tbl: Table, select_items: list[dict[str, Any]]):
        if not select_items:
            raise QueryBuilderError("Campo 'select' é obrigatório.")

        exprs = []
        for item in select_items:
            kind = item.get("kind")
            field = item.get("field")
            alias = item.get("alias")

            if kind == "dimension":
                expr = self._get_column(tbl, field)
            elif kind == "aggregated_field":
                aggregation = item.get("aggregation")
                if not aggregation:
                    raise QueryBuilderError(
                        f"Campo 'aggregation' é obrigatório para aggregated_field: {item}"
                    )
                expr = self._build_aggregation(tbl, aggregation, field)
            else:
                raise QueryBuilderError(f"Tipo de select não suportado: {kind}")

            if alias:
                expr = expr.label(alias)
            exprs.append(expr)

        return exprs

    def _build_aggregation(self, tbl: Table, aggregation: str, field: str):
        agg = aggregation.lower()

        if agg == "count":
            return func.count() if field == "*" else func.count(self._get_column(tbl, field))
        if agg == "count_distinct":
            if field == "*":
                raise QueryBuilderError(
                    "Agregação 'count_distinct' não pode ser usada com campo coringa '*'"
                )
            return func.count(self._get_column(tbl, field).distinct())
        if agg == "sum":
            return func.sum(self._get_column(tbl, field))
        if agg == "avg":
            return func.avg(self._get_column(tbl, field))
        if agg == "min":
            return func.min(self._get_column(tbl, field))
        if agg == "max":
            return func.max(self._get_column(tbl, field))

        raise QueryBuilderError(f"Agregação não suportada: {aggregation}")

    def _build_filters(self, tbl: Table, filters: list[dict[str, Any]]):
        expressions = []

        for f in filters:
            field = f.get("field")
            operator = f.get("operator")
            value = f.get("value")

            if not field or not operator:
                raise QueryBuilderError(f"Filtro inválido: {f}")

            col = self._get_column(tbl, field)
            op = operator.lower()

            if op == "=":
                expressions.append(col == value)
            elif op == "!=":
                expressions.append(col != value)
            elif op == ">":
                expressions.append(col > value)
            elif op == "<":
                expressions.append(col < value)
            elif op == ">=":
                expressions.append(col >= value)
            elif op == "<=":
                expressions.append(col <= value)
            elif op == "like":
                expressions.append(col.like(value))
            elif op == "ilike":
                expressions.append(col.ilike(value))
            elif op == "in":
                if not isinstance(value, list) or not value:
                    raise QueryBuilderError(f"Filtro IN exige lista não vazia: {f}")
                expressions.append(col.in_(value))
            elif op == "not_in":
                if not isinstance(value, list) or not value:
                    raise QueryBuilderError(f"Filtro NOT IN exige lista não vazia: {f}")
                expressions.append(col.not_in(value))
            elif op == "between":
                if not isinstance(value, dict) or "start" not in value or "end" not in value:
                    raise QueryBuilderError(
                        f"Filtro BETWEEN exige value com start e end: {f}"
                    )
                expressions.append(col.between(value["start"], value["end"]))
            elif op == "is_null":
                expressions.append(col.is_(None))
            elif op == "is_not_null":
                expressions.append(col.is_not(None))
            else:
                raise QueryBuilderError(f"Operador não suportado: {operator}")

        return expressions

    def _build_order_by(self, order_by_items: list[dict[str, Any]]):
        result = []
        for item in order_by_items:
            field = item.get("field")
            direction = item.get("direction", "asc").lower()
            if direction == "asc":
                result.append(asc(field))
            elif direction == "desc":
                result.append(desc(field))
            else:
                raise QueryBuilderError(f"Direção inválida no order_by: {direction}")
        return result

    def _get_column(self, tbl: Table, field: str):
        if field == "*":
            raise QueryBuilderError("'*' só pode ser usado em algumas agregações, como count.")
        return tbl.c[field]
