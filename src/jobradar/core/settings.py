"""Typed application settings loaded from the environment."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
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
    config_dir: Path = Path("config")  # source_policies.yaml, connectors.yaml, companies.yaml, …
    packs_dir: Path = Path("packs")

    # Database timeouts (docs/coding-standards.md §6)
    db_connect_timeout_seconds: int = Field(default=5, ge=1)
    db_statement_timeout_ms: int = Field(default=15_000, ge=100)
    db_lock_timeout_ms: int = Field(default=5_000, ge=100)
    # Login-less roles every transaction switches into (row-level security, database.md §4).
    db_app_role: str = Field(default="jobradar_app", pattern=r"^[a-z_][a-z0-9_]*$")
    db_corpus_role: str = Field(default="jobradar_corpus", pattern=r"^[a-z_][a-z0-9_]*$")

    # Outbound HTTP (core.http): timeouts, retries, politeness
    http_user_agent: str = "JobRadar/0.1"
    http_contact: str | None = None  # email or URL appended to the User-Agent for site owners
    http_connect_timeout_seconds: float = Field(default=5, gt=0)
    http_read_timeout_seconds: float = Field(default=20, gt=0)
    http_total_timeout_seconds: float = Field(default=30, gt=0)
    http_max_attempts: int = Field(default=4, ge=1, le=10)
    http_max_redirects: int = Field(default=3, ge=0, le=10)
    http_max_response_bytes: int = Field(default=10_000_000, ge=1_000)
    http_retry_after_cap_seconds: float = Field(default=60, gt=0)

    # Source credentials (owner's accounts; only in .env, never committed)
    adzuna_app_id: str | None = None
    adzuna_app_key: SecretStr | None = None

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

    @property
    def http_user_agent_header(self) -> str:
        """User-Agent sent on every outbound request, with the contact if configured."""
        if self.http_contact:
            return f"{self.http_user_agent} (+{self.http_contact})"
        return self.http_user_agent


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
