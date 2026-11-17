"""Infraestructura de acceso a PostgreSQL mediante SQLAlchemy."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from payment_reference_service.config import load_settings


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
    """Clase base declarativa para los modelos SQLAlchemy del servicio."""


settings = load_settings()

# Si PostgreSQL no responde, la conexión falla en un tiempo acotado (no queda
# esperando): la solicitud responde 503 y /health/ready no se bloquea. Con
# `pool_pre_ping` las conexiones rotas se descartan y el pool se recupera solo
# cuando la base vuelve (GAP-PR-19).
DB_CONNECT_TIMEOUT_SECONDS = 5

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    **pool_options(),
    connect_args={"connect_timeout": DB_CONNECT_TIMEOUT_SECONDS},
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)


def get_db_session() -> Generator[Session, None, None]:
    """Proporciona una sesión SQLAlchemy por solicitud.

    La dependencia únicamente administra el ciclo de vida de la sesión.
    No realiza commit ni rollback automáticamente. Esa responsabilidad
    corresponde a los repositorios y casos de persistencia que ejecuten
    operaciones de escritura.

    Yields:
        Sesión SQLAlchemy activa.
    """
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


def is_database_ready() -> bool:
    """Comprueba si PostgreSQL se encuentra disponible.

    Ejecuta una consulta mínima contra el motor sin modificar datos.

    Returns:
        `True` si PostgreSQL responde correctamente; `False` en caso
        contrario.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
