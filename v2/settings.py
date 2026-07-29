from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str
    CLICKHOUSE_DB_URL: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.1
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    model_config = {"env_file": ".env.langchain.local"}
