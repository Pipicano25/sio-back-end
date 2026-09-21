"""Fixtures compartidos para las pruebas de geography-service."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(
    PROJECT_ROOT / ".env",
    override=False,
)

_TEST_TABLES = (
    "global_cities",
    "global_administrative_divisions",
    "global_countries",
)


def _get_test_database_url() -> str:
    """Obtiene y valida la URL de la base de datos de pruebas.

    La función exige una variable específica de testing y además comprueba
    que el nombre de la base de datos contenga la palabra ``test``. Esta
    segunda validación reduce el riesgo de ejecutar pruebas destructivas
    contra una base de datos de desarrollo o producción.

    Returns:
        URL SQLAlchemy de la base de datos PostgreSQL utilizada por pytest.

    Raises:
        RuntimeError: Si la variable no existe, está vacía o apunta a una
            base cuyo nombre no parece corresponder a testing.
    """
    value = os.getenv(
        "GEOGRAPHY_TEST_DATABASE_URL",
    )

    if value is None or not value.strip():
        raise RuntimeError(
            "La variable GEOGRAPHY_TEST_DATABASE_URL "
            "es obligatoria para ejecutar las pruebas."
        )

    database_url = value.strip()
    database_name = make_url(
        database_url,
    ).database

    if (
        database_name is None
        or "test" not in database_name.lower()
    ):
        raise RuntimeError(
            "GEOGRAPHY_TEST_DATABASE_URL debe apuntar "
            "a una base de datos exclusiva de pruebas."
        )

    return database_url


def _build_alembic_config() -> AlembicConfig:
    """Construye la configuración de Alembic para las pruebas.

    Returns:
        Configuración de Alembic apuntando al proyecto actual.
    """
    config = AlembicConfig(
        str(PROJECT_ROOT / "alembic.ini"),
    )

    config.set_main_option(
        "script_location",
        str(PROJECT_ROOT / "alembic"),
    )

    return config


def _check_database_connection(
    database_url: str,
) -> None:
    """Comprueba que PostgreSQL de testing esté disponible.

    Args:
        database_url: URL SQLAlchemy de la base de datos de pruebas.

    Raises:
        RuntimeError: Si no es posible establecer conexión.
    """
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT 1"),
            )

    except SQLAlchemyError as exc:
        raise RuntimeError(
            "No fue posible conectar con PostgreSQL de pruebas. "
            "Verifique que geography-test-db esté iniciado."
        ) from exc

    finally:
        engine.dispose()


def _truncate_test_tables(
    engine: Engine,
) -> None:
    """Elimina los registros de las tablas funcionales de testing.

    Solo se consideran nombres de tablas definidos internamente por la suite
    de pruebas. Esto permite comenzar cada prueba de persistencia con un estado
    conocido sin recrear todo el esquema.

    Args:
        engine: Engine conectado exclusivamente a la base de datos de pruebas.
    """
    inspector = inspect(
        engine,
    )

    existing_tables = set(
        inspector.get_table_names(),
    )

    tables = [
        table
        for table in _TEST_TABLES
        if table in existing_tables
    ]

    if not tables:
        return

    table_names = ", ".join(
        f'"{table}"'
        for table in tables
    )

    statement = text(
        f"TRUNCATE TABLE {table_names} "
        "RESTART IDENTITY CASCADE"
    )

    with engine.begin() as connection:
        connection.execute(
            statement,
        )


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Proporciona la URL validada de PostgreSQL de testing.

    Returns:
        URL SQLAlchemy de la base de datos utilizada por la suite.
    """
    return _get_test_database_url()


@pytest.fixture(scope="session")
def migrated_database(
    test_database_url: str,
) -> Generator[None, None, None]:
    """Aplica todas las migraciones Alembic sobre la base de pruebas.

    Antes de ejecutar Alembic se reemplaza temporalmente ``DATABASE_URL`` por
    la URL exclusiva de testing. Esto funciona con el ``env.py`` actual,
    donde la configuración de Alembic obtiene la conexión mediante Settings.

    Args:
        test_database_url: URL validada de PostgreSQL de pruebas.

    Yields:
        Control a la suite después de ejecutar ``alembic upgrade head``.
    """
    _check_database_connection(
        test_database_url,
    )

    previous_database_url = os.environ.get(
        "DATABASE_URL",
    )

    os.environ["DATABASE_URL"] = (
        test_database_url
    )

    try:
        config = _build_alembic_config()

        command.upgrade(
            config,
            "head",
        )

        yield

    finally:
        if previous_database_url is None:
            os.environ.pop(
                "DATABASE_URL",
                None,
            )
        else:
            os.environ["DATABASE_URL"] = (
                previous_database_url
            )


@pytest.fixture(scope="session")
def test_engine(
    test_database_url: str,
    migrated_database: None,
) -> Generator[Engine, None, None]:
    """Crea el engine SQLAlchemy compartido por la suite de persistencia.

    Args:
        test_database_url: URL de PostgreSQL de pruebas.
        migrated_database: Fixture que garantiza la ejecución de Alembic.

    Yields:
        Engine conectado exclusivamente a la base de datos de testing.
    """
    engine = create_engine(
        test_database_url,
        pool_pre_ping=True,
    )

    try:
        yield engine

    finally:
        engine.dispose()


@pytest.fixture
def clean_database(
    test_engine: Engine,
) -> Generator[None, None, None]:
    """Garantiza una base funcional vacía antes y después de una prueba.

    Args:
        test_engine: Engine exclusivo de PostgreSQL de pruebas.

    Yields:
        Control a la prueba con las tablas funcionales vacías.
    """
    _truncate_test_tables(
        test_engine,
    )

    yield

    _truncate_test_tables(
        test_engine,
    )


@pytest.fixture
def db_session(
    test_engine: Engine,
    clean_database: None,
) -> Generator[Session, None, None]:
    """Proporciona una sesión SQLAlchemy aislada para una prueba.

    Args:
        test_engine: Engine de PostgreSQL de testing.
        clean_database: Fixture que garantiza tablas funcionales vacías.

    Yields:
        Sesión SQLAlchemy disponible durante una única prueba.
    """
    session_factory = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    with session_factory() as session:
        try:
            yield session

        finally:
            session.rollback()
