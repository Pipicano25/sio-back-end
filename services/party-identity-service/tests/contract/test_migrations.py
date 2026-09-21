"""Pruebas de contrato para el esquema PostgreSQL de party-identity-service."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def test_database_is_available(
    test_engine: Engine,
) -> None:
    """Comprueba que PostgreSQL de testing responda correctamente."""
    with test_engine.connect() as connection:
        result = connection.execute(
            text("SELECT 1"),
        )

        assert result.scalar_one() == 1


def test_migrations_create_expected_tables(
    test_engine: Engine,
) -> None:
    """Comprueba que Alembic cree las tablas funcionales esperadas."""
    inspector = inspect(
        test_engine,
    )

    tables = set(
        inspector.get_table_names(),
    )

    expected_tables = {
        "person_identities",
        "identification_type_rules",
        "organization_identities",
    }

    assert expected_tables.issubset(
        tables,
    )


def test_organization_identities_does_not_have_verification_digit(
    test_engine: Engine,
) -> None:
    """Comprueba que la tabla de organizaciones no conserve DV separado."""
    inspector = inspect(
        test_engine,
    )

    columns = {
        column["name"]
        for column in inspector.get_columns(
            "organization_identities",
        )
    }

    assert "verification_digit" not in columns


def test_migrations_seed_active_colombian_organization_nit_rule(
    test_engine: Engine,
) -> None:
    """Comprueba que exista la regla activa NIT para organizaciones."""
    with test_engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    party_kind,
                    identification_type,
                    sigla,
                    number_pattern
                FROM identification_type_rules
                WHERE party_kind = 'ORGANIZATION'
                  AND country_id =
                    'cf160c2d-b6de-4ef5-9257-a0a8539058d9'
                  AND sigla = 'NIT'
                  AND is_active = true
                """
            )
        ).mappings().one()

    assert row["party_kind"] == "ORGANIZATION"
    assert row["identification_type"] == "TAX_ID"
    assert row["sigla"] == "NIT"
    assert row["number_pattern"] == "^[A-Z0-9]{4,11}-[0-9]$"
