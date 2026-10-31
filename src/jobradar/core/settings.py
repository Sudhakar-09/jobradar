"""Typed application settings loaded from the environment."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings; invalid values stop the process at startup."""

    app_name: str = "JobRadar"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://jobradar:local_dev_only@localhost:5432/jobradar"
    redis_host: str = "localhost"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    health_check_timeout_seconds: int = Field(default=2, ge=1)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def redis_url(self) -> str:
        """Redis URL built from host and port."""
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
