from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_CONNECT_TIMEOUT_SECONDS = 5
"""Tiempo de espera de conexión a PostgreSQL (Principio X, feature 009)."""


class Base(DeclarativeBase):
    """Clase base para los futuros modelos SQLAlchemy."""


class Database:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
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