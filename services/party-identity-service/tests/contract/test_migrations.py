"""Pruebas de contrato del esquema PostgreSQL (FR-064, data-model).

Las migraciones se aplican desde cero sobre una base vacía en un fixture
propio: se reinicia el esquema `public` y se ejecuta `upgrade head`. No se usa
`downgrade base` porque las migraciones históricas `0001`–`0010` (intocables,
Principio VIII) no son reversibles hasta el origen con sus propios datos.
"""

from collections.abc import Generator

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from tests.conftest import build_alembic_config

PREVIOUS_HEAD = "0010_org_nit_rule_no_dv"
AUDITED_TABLES = (
    "identification_type_rules",
    "person_identities",
    "organization_identities",
)
STATUS_TABLES = (
    "person_identities",
    "organization_identities",
)


@pytest.fixture(scope="module")
def fresh_schema(test_engine: Engine) -> Generator[Engine, None, None]:
    """Reconstruye el esquema desde cero para las pruebas de este módulo."""
    reset_schema(test_engine)
    command.upgrade(build_alembic_config(), "head")
    yield test_engine


def reset_schema(engine: Engine) -> None:
    """Deja la base de pruebas vacía (sin tablas ni `alembic_version`)."""
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


def _columns(engine: Engine, table: str) -> dict[str, dict]:
    return {
        column["name"]: column
        for column in inspect(engine).get_columns(table)
    }


def test_migrations_create_expected_tables(fresh_schema: Engine) -> None:
    tables = set(inspect(fresh_schema).get_table_names())

    assert set(AUDITED_TABLES).issubset(tables)


@pytest.mark.parametrize("table", STATUS_TABLES)
def test_status_column_check_and_index(fresh_schema: Engine, table: str) -> None:
    inspector = inspect(fresh_schema)
    column = _columns(fresh_schema, table)["status"]

    assert column["nullable"] is False
    assert str(column["type"]).startswith("VARCHAR(20)")
    assert "ACTIVE" in str(column["default"])

    checks = {check["name"]: check["sqltext"] for check in inspector.get_check_constraints(table)}
    assert f"ck_{table}_status" in checks
    assert "ACTIVE" in checks[f"ck_{table}_status"]
    assert "INACTIVE" in checks[f"ck_{table}_status"]

    indexes = {index["name"] for index in inspector.get_indexes(table)}
    assert f"ix_{table}_status" in indexes


@pytest.mark.parametrize("table", STATUS_TABLES)
def test_status_check_rejects_unknown_value(fresh_schema: Engine, table: str) -> None:
    with fresh_schema.connect() as connection:
        definition = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = :name"
            ),
            {"name": f"ck_{table}_status"},
        ).scalar_one()

    assert "ACTIVE" in definition and "INACTIVE" in definition


@pytest.mark.parametrize("table", AUDITED_TABLES)
def test_audit_actor_columns_are_text(fresh_schema: Engine, table: str) -> None:
    columns = _columns(fresh_schema, table)

    for name in ("created_by", "updated_by"):
        assert str(columns[name]["type"]) == "VARCHAR(255)"
        assert columns[name]["nullable"] is False


def test_organization_identities_does_not_have_verification_digit(fresh_schema: Engine) -> None:
    assert "verification_digit" not in _columns(fresh_schema, "organization_identities")


def test_downgrade_to_previous_head_and_upgrade_again(fresh_schema: Engine) -> None:
    config = build_alembic_config()

    command.downgrade(config, PREVIOUS_HEAD)
    person_columns = _columns(fresh_schema, "person_identities")
    assert "status" not in person_columns
    assert "UUID" in str(person_columns["created_by"]["type"]).upper()

    command.upgrade(config, "head")
    assert "status" in _columns(fresh_schema, "person_identities")


def test_downgrade_fails_explicitly_with_non_uuid_actors(fresh_schema: Engine) -> None:
    config = build_alembic_config()

    with fresh_schema.begin() as connection:
        connection.execute(text("UPDATE identification_type_rules SET created_by = 'system:x'"))
        count = connection.execute(text("SELECT count(*) FROM identification_type_rules")).scalar_one()

    if count == 0:
        pytest.skip("Sin reglas de migración para probar la reversión con actores de texto.")

    try:
        with pytest.raises(RuntimeError, match="no son UUID"):
            command.downgrade(config, "0011_add_identity_status")
    finally:
        with fresh_schema.begin() as connection:
            connection.execute(text("TRUNCATE TABLE identification_type_rules"))
        command.upgrade(config, "head")


# --------------------------------------------------------------------------
# Fase B (T012; FR-094, Principio VIII)
# --------------------------------------------------------------------------

PHASE_A_HEAD = "0012_audit_actor_as_text"
PHASE_B_TABLES = (
    "global_business_sectors",
    "person_contact_profiles",
    "organization_contact_profiles",
    "organization_contact_persons",
    "organization_business_sectors",
    "organization_legal_representatives",
)


def test_phase_b_tables_exist_with_audit_and_version(fresh_schema: Engine) -> None:
    tables = set(inspect(fresh_schema).get_table_names())
    assert set(PHASE_B_TABLES).issubset(tables)

    for table in PHASE_B_TABLES:
        columns = _columns(fresh_schema, table)
        for name in ("created_by", "updated_by"):
            assert str(columns[name]["type"]) == "VARCHAR(255)"
            assert columns[name]["nullable"] is False
        for name in ("created_at", "updated_at", "version"):
            assert columns[name]["nullable"] is False


def test_legal_representatives_has_no_created_by_user_id(fresh_schema: Engine) -> None:
    """C-02: el estándar usa `created_by_user_id`; prevalece D1."""
    columns = _columns(fresh_schema, "organization_legal_representatives")

    assert "created_by_user_id" not in columns
    assert str(columns["source_document_reference"]["type"]) == "VARCHAR(1000)"


def test_downgrade_to_phase_a_head_removes_phase_b_and_keeps_phase_a(fresh_schema: Engine) -> None:
    config = build_alembic_config()

    command.downgrade(config, PHASE_A_HEAD)
    tables = set(inspect(fresh_schema).get_table_names())
    assert not set(PHASE_B_TABLES) & tables
    assert set(AUDITED_TABLES).issubset(tables)

    command.upgrade(config, "head")
    assert set(PHASE_B_TABLES).issubset(set(inspect(fresh_schema).get_table_names()))


def test_upgrade_over_phase_a_data_preserves_rows(fresh_schema: Engine) -> None:
    config = build_alembic_config()
    command.downgrade(config, PHASE_A_HEAD)

    with fresh_schema.begin() as connection:
        connection.execute(text(
            "INSERT INTO person_identities (id, identification_country_id, identification_type, "
            "identification_number, first_name, last_name, verification_status, status, version, "
            "created_by, updated_by) VALUES (gen_random_uuid(), gen_random_uuid(), 'CC', "
            "'1000000999', 'ANA', 'PRUEBA', 'UNVERIFIED', 'ACTIVE', 1, 'user-a', 'user-a')"
        ))
        connection.execute(text(
            "INSERT INTO organization_identities (id, country_id, identification_type, "
            "identification_number, legal_name, status, version, created_by, updated_by) "
            "VALUES (gen_random_uuid(), gen_random_uuid(), 'NIT', '900000999-1', "
            "'ORGANIZACION FICTICIA', 'ACTIVE', 1, 'user-a', 'user-a')"
        ))
        before = connection.execute(text(
            "SELECT (SELECT count(*) FROM person_identities), "
            "(SELECT count(*) FROM organization_identities), "
            "(SELECT count(*) FROM identification_type_rules)"
        )).one()

    try:
        command.upgrade(config, "head")

        with fresh_schema.connect() as connection:
            after = connection.execute(text(
                "SELECT (SELECT count(*) FROM person_identities), "
                "(SELECT count(*) FROM organization_identities), "
                "(SELECT count(*) FROM identification_type_rules)"
            )).one()

        assert tuple(after) == tuple(before)
    finally:
        with fresh_schema.begin() as connection:
            connection.execute(text("TRUNCATE TABLE person_identities, organization_identities CASCADE"))


# --------------------------------------------------------------------------
# 0018: `name` del sector a 255 (CIIU Rev. 5 A.C., T112)
# --------------------------------------------------------------------------

def test_business_sector_name_allows_official_ciiu_titles(fresh_schema: Engine) -> None:
    columns = _columns(fresh_schema, "global_business_sectors")

    assert str(columns["name"]["type"]) == "VARCHAR(255)"


def test_downgrade_0018_fails_with_long_sector_names(fresh_schema: Engine) -> None:
    config = build_alembic_config()

    with fresh_schema.begin() as connection:
        connection.execute(text(
            "INSERT INTO global_business_sectors (id, classification_system, code, name, created_by, "
            "updated_by) VALUES (gen_random_uuid(), 'PRUEBA', '15', :name, 'system:x', 'system:x')"
        ), {"name": "x" * 222})

    try:
        with pytest.raises(RuntimeError, match="180 caracteres"):
            command.downgrade(config, "0017_create_legal_reps")
    finally:
        with fresh_schema.begin() as connection:
            connection.execute(text("TRUNCATE TABLE global_business_sectors CASCADE"))
        command.upgrade(config, "head")

    command.downgrade(config, "0017_create_legal_reps")
    assert str(_columns(fresh_schema, "global_business_sectors")["name"]["type"]) == "VARCHAR(180)"
    command.upgrade(config, "head")
