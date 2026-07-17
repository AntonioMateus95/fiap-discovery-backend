import pandas as pd
from sqlalchemy import create_engine, text


def execute_sql(sql: str, database_url: str) -> str:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        df = pd.DataFrame(result.fetchall(), columns=list(result.keys()))

    if df.empty:
        return "[]"
    return df.to_string(index=False)
