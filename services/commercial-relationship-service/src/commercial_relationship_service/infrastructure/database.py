"""Infraestructura de acceso a PostgreSQL mediante SQLAlchemy."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_CONNECT_TIMEOUT_SECONDS = 5
"""Tiempo de espera de conexión a PostgreSQL (Principio X, feature 009)."""

NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
}


class Base(DeclarativeBase):
    """Clase base declarativa con nombres de restricción explícitos (Principio VIII)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Database:
    """Agrupa el engine y la fábrica de sesiones SQLAlchemy."""

    def __init__(self, database_url: str) -> None:
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
        """Ejecuta una consulta mínima para comprobar PostgreSQL (`/health/ready`)."""
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def dispose(self) -> None:
        """Libera el pool de conexiones del engine."""
        self.engine.dispose()


def get_db_session(request: Request) -> Generator[Session, None, None]:
    """Proporciona una sesión SQLAlchemy por solicitud.

    Solo administra el ciclo de vida; los repositorios confirman o revierten.
    """
    database: Database = request.app.state.database

    with database.session_factory() as session:
        yield session
