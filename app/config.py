from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "School Results API"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/school_results"

    # Development default only. Set JWT_SECRET_KEY in the environment for any real deployment.
    jwt_secret_key: str = "dev-only-secret-key-change-me-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # A student is flagged "at risk" if their latest term average is below this...
    at_risk_score_threshold: float = 50.0
    # ...or if their average dropped by at least this many points since the previous term.
    at_risk_drop_threshold: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
