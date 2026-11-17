import os
from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_CONNECT_TIMEOUT_SECONDS = 5
"""Tiempo de espera de conexión a PostgreSQL (Principio X, feature 009)."""


# Pool acotado del motor propio (spec 025, research R6): `DB_POOL_SIZE` (1–20) y `DB_MAX_OVERFLOW` (0–20).
DB_POOL_SIZE_DEFAULT = 3
DB_MAX_OVERFLOW_DEFAULT = 2


def _pool_option(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = minimum - 1
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} debe ser un entero entre {minimum} y {maximum}")
    return value


def pool_options() -> dict[str, int]:
    """Tamaño del pool del motor propio, leído del entorno al crear el engine."""
    return {
        "pool_size": _pool_option("DB_POOL_SIZE", DB_POOL_SIZE_DEFAULT, 1, 20),
        "max_overflow": _pool_option("DB_MAX_OVERFLOW", DB_MAX_OVERFLOW_DEFAULT, 0, 20),
    }


class Base(DeclarativeBase):
    """Clase base para los futuros modelos SQLAlchemy."""


class Database:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            **pool_options(),
            connect_args={"connect_timeout": DB_CONNECT_TIMEOUT_SECONDS},
        )

        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def check_connection(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(
                text("SELECT 1"),
            )

    def dispose(self) -> None:
        self.engine.dispose()


def get_db_session(
    request: Request,
) -> Generator[Session, None, None]:
    database: Database = request.app.state.database

    with database.session_factory() as session:
        yield session