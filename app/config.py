from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = "not-needed"
    database_url: str
    embed_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    embed_dim: int = 1536

    ollama_base_url: str = ""

    search_api_key: str = ""

    # CORS: comma-separated allowed origins for the browser client; "*" = all
    cors_origins: str = "*"

    # pool sizing — see C1 Concept block B
    pool_size: int = 10
    max_overflow: int = 20

    @property
    def cors_origin_list(self) -> list[str]:
        s = self.cors_origins.strip()
        return ["*"] if s == "*" else [o.strip() for o in s.split(",") if o.strip()]

    @property
    def checkpoint_url(self) -> str:
        """psycopg-style URL for LangGraph's AsyncPostgresSaver.

        SQLAlchemy talks to Postgres over the async ``postgresql+asyncpg://``
        driver; the checkpointer uses psycopg and wants the plain
        ``postgresql://`` form. Both are derived from one env var.
        """
        return self.database_url.replace("postgresql+asyncpg", "postgresql")


settings = Settings()
