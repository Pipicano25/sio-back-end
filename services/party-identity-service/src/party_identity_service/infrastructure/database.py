"""Infraestructura de acceso a PostgreSQL mediante SQLAlchemy."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_CONNECT_TIMEOUT_SECONDS = 5
"""Tiempo de espera de conexión a PostgreSQL (Principio X, feature 009)."""


class Base(DeclarativeBase):
    """Clase base declarativa para los modelos SQLAlchemy del servicio."""


class Database:
    """Agrupa el engine y la fábrica de sesiones SQLAlchemy."""

    def __init__(self, database_url: str) -> None:
        """Inicializa la infraestructura de conexión.

        Args:
            database_url: URL de conexión hacia PostgreSQL.
        """
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": DB_CONNECT_TIMEOUT_SECONDS},
        )

        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )

    def check_connection(self) -> None:
        """Ejecuta una consulta mínima para comprobar PostgreSQL."""
        with self.engine.connect() as connection:
            connection.execute(
                text("SELECT 1"),
            )

    def dispose(self) -> None:
        """Libera el pool de conexiones del engine."""
        self.engine.dispose()


def get_db_session(
    request: Request,
) -> Generator[Session, None, None]:
    """Proporciona una sesión SQLAlchemy por solicitud.

    La dependencia únicamente administra el ciclo de vida de la sesión.
    No realiza commit ni rollback automáticamente.

    Args:
        request: Request actual de FastAPI.

    Yields:
        Sesión SQLAlchemy activa.
    """
    database: Database = request.app.state.database

    with database.session_factory() as session:
        yield session
