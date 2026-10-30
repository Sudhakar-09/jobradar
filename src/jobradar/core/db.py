from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from jobradar.core.settings import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        connect_args={"connect_timeout": settings.health_check_timeout_seconds},
        pool_pre_ping=True,
    )