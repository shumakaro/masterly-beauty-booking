from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    if not url:
        raise AppError(503, "DATABASE_UNAVAILABLE", "Сервис временно недоступен.")
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)


def get_db() -> Generator[Session]:
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session
