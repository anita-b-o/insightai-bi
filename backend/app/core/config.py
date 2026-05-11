from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "InsightAI BI API"
    app_env: str = "development"
    api_v1_prefix: str = "/api"
    secret_key: str
    access_token_expire_minutes: int = 60

    postgres_server: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "insightai"
    postgres_password: str = "insightai"
    postgres_db: str = "insightai_bi"

    backend_cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    storage_path: str = "storage/datasets"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: float = 45.0
    openai_max_retries: int = 1
    ai_sql_max_retries: int = 1
    dashboard_refresh_lock_timeout_seconds: int = 300
    worker_heartbeat_timeout_seconds: int = 180
    sentry_dsn: str | None = None
    sentry_environment: str | None = None
    sentry_release: str | None = None
    sentry_traces_sample_rate: float = 0.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def storage_dir(self) -> Path:
        return Path(self.storage_path)

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        value = value.strip()
        if value.startswith("["):
            import json

            return json.loads(value)
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.app_env.lower() == "production":
        if settings.secret_key == "change-me-to-a-long-random-secret":
            raise ValueError("SECRET_KEY must be overridden in production")
        if settings.openai_api_key and settings.openai_api_key == "replace-me":
            raise ValueError("OPENAI_API_KEY must be overridden in production")
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
