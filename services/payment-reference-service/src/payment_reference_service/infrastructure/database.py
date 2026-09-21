"""Infraestructura de acceso a PostgreSQL mediante SQLAlchemy."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from payment_reference_service.config import load_settings


class Base(DeclarativeBase):
    """Clase base declarativa para los modelos SQLAlchemy del servicio."""


settings = load_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
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
