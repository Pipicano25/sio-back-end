"""Migraciones desde cero y esquema resultante (FR-067, RC-11, data-model.md)."""

import pytest
from sqlalchemy import create_engine, inspect, text

from tests.conftest import run_alembic

pytestmark = pytest.mark.usefixtures("migrated_database")


@pytest.fixture
def fresh_schema(test_database_url):
    """Baja a base y vuelve a head: la migración se aplica sobre una base vacía."""
    run_alembic(test_database_url, "downgrade", "base")
    run_alembic(test_database_url, "upgrade", "head")
    engine = create_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()


def _columns(engine, table):
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT column_name, data_type, character_maximum_length, is_nullable, "
                "column_default, numeric_precision, numeric_scale "
                "FROM information_schema.columns WHERE table_name = :table"
            ),
            {"table": table},
        ).mappings()
        return {row["column_name"]: row for row in rows}


def test_companies_columns(fresh_schema):
    columns = _columns(fresh_schema, "companies")

    assert columns["organization_identity_id"]["data_type"] == "uuid"
    assert columns["organization_identity_id"]["is_nullable"] == "NO"
    assert columns["timezone"]["character_maximum_length"] == 60
    assert columns["timezone"]["is_nullable"] == "NO"
    assert "America/Bogota" in columns["timezone"]["column_default"]
    assert columns["default_currency"]["data_type"] == "character"
    assert columns["default_currency"]["character_maximum_length"] == 3
    assert "COP" in columns["default_currency"]["column_default"]
    assert columns["status"]["character_maximum_length"] == 20
    assert "ACTIVE" in columns["status"]["column_default"]
    assert (columns["latitude"]["numeric_precision"], columns["latitude"]["numeric_scale"]) == (9, 6)
    assert (columns["longitude"]["numeric_precision"], columns["longitude"]["numeric_scale"]) == (9, 6)
    assert columns["email"]["character_maximum_length"] == 254
    assert columns["phone"]["character_maximum_length"] == 40
    assert columns["postal_code"]["character_maximum_length"] == 20
    assert columns["version"]["data_type"] == "integer"
    assert columns["version"]["is_nullable"] == "NO"

    for audit in ("created_by", "updated_by"):
        assert columns[audit]["data_type"] == "character varying"
        assert columns[audit]["character_maximum_length"] == 255

    for column in ("country_id", "administrative_division_id", "city_id"):
        assert columns[column]["data_type"] == "uuid"
        assert columns[column]["is_nullable"] == "YES"


def test_companies_do_not_store_data_owned_by_party_identity(fresh_schema):
    """DS-01, DS-13, RC-11: ni identificación ni razón social ni nombre comercial."""
    columns = _columns(fresh_schema, "companies")

    for forbidden in ("identification_type", "identification_number", "legal_name", "trade_name"):
        assert forbidden not in columns


def test_no_columns_copy_geography_data(fresh_schema):
    """RC-11: solo UUID de geografía, sin nombres ni códigos."""
    for table in ("companies", "branches"):
        columns = _columns(fresh_schema, table)
        for forbidden in ("country_name", "city_name", "division_name", "iso2_code", "iso3_code"):
            assert forbidden not in columns


def test_branches_columns(fresh_schema):
    columns = _columns(fresh_schema, "branches")

    assert columns["company_id"]["is_nullable"] == "NO"
    assert columns["code"]["character_maximum_length"] == 40
    assert columns["name"]["character_maximum_length"] == 160
    assert columns["timezone"]["is_nullable"] == "YES"
    assert columns["timezone"]["column_default"] is None
    assert columns["version"]["is_nullable"] == "NO"
    assert columns["created_by"]["character_maximum_length"] == 255


def test_no_person_columns_in_phase_a(fresh_schema):
    """R-15: la Fase A no guarda personas ni usuarios."""
    for table in ("companies", "branches"):
        columns = _columns(fresh_schema, table)
        assert not {"person_identity_id", "application_user_id", "keycloak_sub"} & set(columns)


def test_only_phase_a_tables_exist(fresh_schema):
    tables = set(inspect(fresh_schema).get_table_names())

    assert {"companies", "branches"} <= tables
    assert not {"application_users", "user_branches", "company_advisor_assignments"} & tables


def test_downgrade_removes_tables_and_upgrade_restores(test_database_url, fresh_schema):
    run_alembic(test_database_url, "downgrade", "base")
    assert not {"companies", "branches"} & set(inspect(fresh_schema).get_table_names())

    run_alembic(test_database_url, "upgrade", "head")
    assert {"companies", "branches"} <= set(inspect(fresh_schema).get_table_names())
