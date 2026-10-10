"""Migración 0020 y `seed`: país de las 8 reglas colombianas históricas (G-017-01).

Cada prueba reconstruye el esquema (como `test_migrations.py`) y lo deja en `head` con las tablas
vacías al terminar. `PARTY_IDENTITY_SEED_COUNTRY_ID` es el UUID de Colombia del entorno; en las
pruebas, el país ficticio `COLOMBIA_ID`.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Generator

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from party_identity_service.seed.constants import HISTORIC_RULE_IDS, SEED_ACTOR
from party_identity_service.seed.data import COLOMBIAN_RULES
from party_identity_service.seed.loader import HistoricRuleCountryMismatchError, load_seed
from tests.conftest import COLOMBIA_ID, PROJECT_ROOT, build_alembic_config
from tests.contract.test_migrations import reset_schema

VARIABLE = "PARTY_IDENTITY_SEED_COUNTRY_ID"
PREVIOUS = "0019_audit_outbox"
HISTORIC_COUNTRY = "cf160c2d-b6de-4ef5-9257-a0a8539058d9"
CORRECTIONS = "identification_type_rule_country_corrections"
CONTENT = (
    "party_kind", "identification_type", "sigla", "number_pattern", "number_pattern_description",
    "example_value", "min_age_years", "max_age_years", "valid_from", "created_by", "created_at",
)


def _migration():
    path = PROJECT_ROOT / "alembic" / "versions" / "0020_fix_colombia_rule_country.py"
    spec = importlib.util.spec_from_file_location("migration_0020", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def schema(test_engine: Engine) -> Generator[Engine, None, None]:
    reset_schema(test_engine)
    yield test_engine
    reset_schema(test_engine)
    command.upgrade(build_alembic_config(), "head")


def _rules(engine: Engine) -> list[dict]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(
            text("SELECT * FROM identification_type_rules ORDER BY id")
        ).mappings()]


def _revision(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def _orphans(engine: Engine, existing_countries: set) -> list[dict]:
    """Validador sobre la base: reglas cuyo país no está entre los existentes."""
    return [rule for rule in _rules(engine) if rule["country_id"] not in existing_countries]


def _insert_seed_copies(engine: Engine, country_id=COLOMBIA_ID) -> None:
    """Estado del entorno de la 017: el `seed` creó las 8 reglas con el país real."""
    with engine.begin() as connection:
        for rule in COLOMBIAN_RULES:
            connection.execute(
                text(
                    "INSERT INTO identification_type_rules (id, party_kind, country_id, identification_type, "
                    "sigla, number_pattern, number_pattern_description, example_value, min_age_years, "
                    "max_age_years, is_active, version, created_by, updated_by) VALUES (gen_random_uuid(), "
                    ":party_kind, :country, :identification_type, :sigla, :number_pattern, "
                    ":number_pattern_description, :example_value, :min_age_years, :max_age_years, true, 1, "
                    ":actor, :actor)"
                ),
                {**rule, "country": country_id, "actor": SEED_ACTOR},
            )


def _at_previous_with_seed_copies(engine: Engine, monkeypatch) -> list[dict]:
    monkeypatch.setenv(VARIABLE, str(COLOMBIA_ID))
    command.upgrade(build_alembic_config(), PREVIOUS)
    _insert_seed_copies(engine)
    return _rules(engine)


def test_historic_ids_match_between_migration_and_seed() -> None:
    assert _migration().HISTORIC_RULE_IDS == HISTORIC_RULE_IDS
    assert set(HISTORIC_RULE_IDS) == {(rule["party_kind"], rule["identification_type"]) for rule in COLOMBIAN_RULES}


def test_clean_install_ends_with_exactly_eight_colombian_rules(schema: Engine, monkeypatch) -> None:
    monkeypatch.setenv(VARIABLE, str(COLOMBIA_ID))

    command.upgrade(build_alembic_config(), "head")

    rules = _rules(schema)
    assert len(rules) == 8
    assert {str(rule["id"]) for rule in rules} == set(HISTORIC_RULE_IDS.values())
    assert all(rule["is_active"] and rule["country_id"] == COLOMBIA_ID for rule in rules)
    assert _orphans(schema, {COLOMBIA_ID}) == []
    with schema.connect() as connection:
        corrections = connection.execute(text(f"SELECT correction, count(*) FROM {CORRECTIONS} GROUP BY 1")).all()
    assert corrections == [("COUNTRY_CORRECTED", 8)]


def test_seed_after_clean_install_is_idempotent_without_duplicates(schema: Engine, monkeypatch) -> None:
    monkeypatch.setenv(VARIABLE, str(COLOMBIA_ID))
    command.upgrade(build_alembic_config(), "head")

    for _ in range(2):
        with Session(schema) as session:
            stats = load_seed(session, country_id=COLOMBIA_ID)
        assert (stats.created, stats.skipped, stats.warnings) == (0, 8, [])

    rules = _rules(schema)
    assert len(rules) == 8
    assert {str(rule["id"]) for rule in rules} == set(HISTORIC_RULE_IDS.values())


def test_upgrade_from_previous_keeps_historic_rules_and_retires_seed_copies(schema: Engine, monkeypatch) -> None:
    before = {rule["id"]: rule for rule in _at_previous_with_seed_copies(schema, monkeypatch)}
    assert len(before) == 16
    assert sum(rule["country_id"] == COLOMBIA_ID for rule in before.values()) == 8

    command.upgrade(build_alembic_config(), "head")

    after = {rule["id"]: rule for rule in _rules(schema)}
    assert after.keys() == before.keys()  # nada se borra ni se recrea
    historic = {rule_id for rule_id in after if str(rule_id) in HISTORIC_RULE_IDS.values()}
    assert len(historic) == 8
    for rule_id, rule in after.items():
        previous = before[rule_id]
        assert {key: rule[key] for key in CONTENT} == {key: previous[key] for key in CONTENT}
        assert rule["country_id"] == COLOMBIA_ID
        assert rule["version"] == previous["version"] + 1
        assert rule["updated_by"] == "system:party-identity-migration"
        if rule_id in historic:
            assert rule["is_active"] and rule["valid_to"] == previous["valid_to"]
        else:
            assert not rule["is_active"] and rule["valid_to"] is not None
    assert _orphans(schema, {COLOMBIA_ID}) == []
    active = [rule for rule in after.values() if rule["is_active"]]
    assert {rule["id"] for rule in active} == historic


def test_downgrade_restores_exactly_and_upgrade_is_deterministic(schema: Engine, monkeypatch) -> None:
    before = _at_previous_with_seed_copies(schema, monkeypatch)
    config = build_alembic_config()
    command.upgrade(config, "head")
    first = _rules(schema)

    monkeypatch.delenv(VARIABLE)  # el downgrade no necesita el país
    command.downgrade(config, PREVIOUS)

    assert _rules(schema) == before
    assert CORRECTIONS not in inspect(schema).get_table_names()

    monkeypatch.setenv(VARIABLE, str(COLOMBIA_ID))
    command.upgrade(config, "head")
    second = _rules(schema)
    ignore = ("valid_to", "updated_at")
    assert [{k: v for k, v in rule.items() if k not in ignore} for rule in second] == [
        {k: v for k, v in rule.items() if k not in ignore} for rule in first
    ]


@pytest.mark.parametrize("value", [None, "", "  ", "no-es-uuid"])
def test_upgrade_without_valid_country_fails_without_writing(schema: Engine, monkeypatch, value) -> None:
    before = _at_previous_with_seed_copies(schema, monkeypatch)
    if value is None:
        monkeypatch.delenv(VARIABLE)
    else:
        monkeypatch.setenv(VARIABLE, value)

    with pytest.raises(RuntimeError, match=VARIABLE):
        command.upgrade(build_alembic_config(), "head")

    assert _revision(schema) == PREVIOUS
    assert _rules(schema) == before
    assert CORRECTIONS not in inspect(schema).get_table_names()


def test_upgrade_where_colombia_keeps_historic_uuid_changes_nothing(schema: Engine, monkeypatch) -> None:
    monkeypatch.setenv(VARIABLE, HISTORIC_COUNTRY)
    command.upgrade(build_alembic_config(), PREVIOUS)
    before = _rules(schema)

    command.upgrade(build_alembic_config(), "head")

    assert _rules(schema) == before
    assert {str(rule["country_id"]) for rule in before} == {HISTORIC_COUNTRY}


def test_upgrade_refuses_to_retire_a_rule_not_created_by_the_seed(schema: Engine, monkeypatch) -> None:
    before = _at_previous_with_seed_copies(schema, monkeypatch)
    with schema.begin() as connection:
        connection.execute(
            text("UPDATE identification_type_rules SET created_by = 'usuario-real' WHERE country_id = :country "
                 "AND identification_type = 'CITIZEN_ID_MODERN'"),
            {"country": COLOMBIA_ID},
        )
    before = _rules(schema)

    with pytest.raises(RuntimeError, match="no la creó el seed"):
        command.upgrade(build_alembic_config(), "head")

    assert _revision(schema) == PREVIOUS
    assert _rules(schema) == before


def test_upgrade_refuses_unknown_rules_with_historic_country(schema: Engine, monkeypatch) -> None:
    monkeypatch.setenv(VARIABLE, str(COLOMBIA_ID))
    command.upgrade(build_alembic_config(), PREVIOUS)
    with schema.begin() as connection:  # regla ajena a 0006/0010 con el UUID histórico
        connection.execute(
            text(
                "INSERT INTO identification_type_rules (id, party_kind, country_id, identification_type, sigla, "
                "number_pattern, number_pattern_description, is_active, version, created_by, updated_by) VALUES "
                "(gen_random_uuid(), 'PERSON', :country, 'OTHER', 'OT', '^[0-9]+$', 'Otra.', false, 1, 'x', 'x')"
            ),
            {"country": HISTORIC_COUNTRY},
        )
    before = _rules(schema)

    with pytest.raises(RuntimeError, match="no son las 8 reglas"):
        command.upgrade(build_alembic_config(), "head")

    assert _rules(schema) == before


def test_seed_refuses_duplicates_while_historic_rules_point_elsewhere(schema: Engine, monkeypatch) -> None:
    monkeypatch.setenv(VARIABLE, str(COLOMBIA_ID))
    command.upgrade(build_alembic_config(), PREVIOUS)  # migración 0020 pendiente
    before = _rules(schema)

    with Session(schema) as session, pytest.raises(HistoricRuleCountryMismatchError, match="alembic upgrade head"):
        load_seed(session, country_id=COLOMBIA_ID)

    assert _rules(schema) == before
