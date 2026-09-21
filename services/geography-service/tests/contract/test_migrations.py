"""Pruebas de contrato para el esquema PostgreSQL de geography-service."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def test_database_is_available(
    test_engine: Engine,
) -> None:
    """Comprueba que PostgreSQL de testing responda correctamente.

    Args:
        test_engine: Engine configurado contra la base exclusiva de pruebas.
    """
    with test_engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1"),
        )

        assert result.scalar_one() == 1


def test_migrations_create_expected_tables(
    test_engine: Engine,
) -> None:
    """Comprueba que Alembic cree las tablas funcionales esperadas.

    Args:
        test_engine: Engine configurado después de ejecutar las migraciones.
    """
    inspector = inspect(
        test_engine,
    )

    tables = set(
        inspector.get_table_names(),
    )

    expected_tables = {
        "global_countries",
        "global_administrative_divisions",
        "global_cities",
    }

    assert expected_tables.issubset(
        tables,
    )
