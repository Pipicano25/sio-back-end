"""Migración 0023: NIT colombiano estricto (enmienda del 2026-11-18)."""

from collections.abc import Generator

import pytest
from alembic import command
from sqlalchemy import Engine, text

from tests.conftest import COLOMBIA_ID, build_alembic_config
from tests.contract.test_migrations import reset_schema

PREVIOUS = "0022_contract_contact_persons_v1"
TARGET = "0023_strict_co_nit_rule"
OLD = "^[A-Z0-9]{4,11}-[0-9]$"
NEW = "^[0-9]{6,10}-[0-9]$"


@pytest.fixture
def schema(test_engine: Engine, monkeypatch) -> Generator[Engine, None, None]:
    monkeypatch.setenv("PARTY_IDENTITY_SEED_COUNTRY_ID", str(COLOMBIA_ID))
    reset_schema(test_engine)
    command.upgrade(build_alembic_config(), PREVIOUS)
    yield test_engine
    reset_schema(test_engine)
    command.upgrade(build_alembic_config(), "head")


def _nit_rules(engine: Engine) -> list[dict]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(text(
            "SELECT party_kind, number_pattern, example_value, version, updated_by "
            "FROM identification_type_rules WHERE sigla = 'NIT' AND is_active ORDER BY party_kind"
        )).mappings()]


def _revision(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _insert_organization(engine: Engine, number: str) -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO organization_identities (id, country_id, identification_type, identification_number, "
            "legal_name, status, version, created_by, updated_by) VALUES (gen_random_uuid(), :country, 'NIT', "
            ":number, 'ORGANIZACION FICTICIA', 'ACTIVE', 1, 'user-a', 'user-a')"
        ), {"country": COLOMBIA_ID, "number": number})


def test_upgrade_makes_both_nit_rules_numeric_and_downgrade_restores(schema: Engine) -> None:
    before = _nit_rules(schema)
    assert [rule["number_pattern"] for rule in before] == [OLD, OLD]

    command.upgrade(build_alembic_config(), TARGET)

    after = _nit_rules(schema)
    assert [rule["party_kind"] for rule in after] == ["ORGANIZATION", "PERSON"]
    for old, new in zip(before, after):
        assert new["number_pattern"] == NEW
        assert new["example_value"] == "900123456-8"
        assert new["version"] == old["version"] + 1
        assert new["updated_by"] == "system:party-identity-migration"

    command.downgrade(build_alembic_config(), PREVIOUS)

    restored = _nit_rules(schema)
    assert [rule["number_pattern"] for rule in restored] == [OLD, OLD]
    assert [rule["example_value"] for rule in restored] == ["900123456-7", "900123456-7"]


def test_upgrade_fails_without_writing_if_an_active_nit_has_letters(schema: Engine) -> None:
    _insert_organization(schema, "GENERICO-0")
    before = _nit_rules(schema)

    with pytest.raises(RuntimeError, match="0023"):
        command.upgrade(build_alembic_config(), TARGET)

    assert _revision(schema) == PREVIOUS
    assert _nit_rules(schema) == before
