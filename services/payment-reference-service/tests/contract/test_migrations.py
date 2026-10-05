"""Migraciones desde cero y migración incremental de `version` (FR-011, Principio VIII)."""

from __future__ import annotations

from uuid import uuid4

from alembic import command
from sqlalchemy import inspect, text

from payment_reference_service.infrastructure.database import engine
from tests.conftest import alembic_config

PREVIOUS_HEAD = "1e2923297584"


def _columns(table: str) -> dict[str, dict]:
    return {column["name"]: column for column in inspect(engine).get_columns(table)}


def _insert_legacy_condition_type(code: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO global_payment_condition_types "
                "(id, code, name, description, status, created_by, updated_by, created_at, updated_at) "
                "VALUES (:id, :code, 'Previo', NULL, 'ACTIVE', 'seed', 'seed', now(), now())"
            ),
            {"id": uuid4(), "code": code},
        )


def test_upgrade_from_empty_creates_version_column():
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    version = _columns("global_payment_condition_types")["version"]
    assert str(version["type"]).upper() == "INTEGER"
    assert version["nullable"] is False
    assert "1" in str(version["default"])


def test_existing_rows_get_version_one_and_downgrade_removes_only_version():
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, PREVIOUS_HEAD)
    _insert_legacy_condition_type("LEGACY")
    methods_before = set(_columns("global_payment_methods"))

    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version FROM global_payment_condition_types WHERE code = 'LEGACY'")
        ).scalar_one() == 1

    command.downgrade(config, "-1")
    assert "version" not in _columns("global_payment_condition_types")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM global_payment_condition_types WHERE code = 'LEGACY'")
        ).scalar_one() == 1

    command.upgrade(config, "head")
    assert "version" in _columns("global_payment_condition_types")
    assert set(_columns("global_payment_methods")) == methods_before
    assert "version" not in methods_before
