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

    command.downgrade(config, PREVIOUS_HEAD)
    assert "version" not in _columns("global_payment_condition_types")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM global_payment_condition_types WHERE code = 'LEGACY'")
        ).scalar_one() == 1

    command.upgrade(config, "head")
    assert "version" in _columns("global_payment_condition_types")
    assert set(_columns("global_payment_methods")) == methods_before
    assert "version" not in methods_before


def _insert_method(code: str) -> str:
    method_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO global_payment_methods "
                "(id, code, name, method_type, requires_reference, status, created_by, updated_by, created_at, updated_at) "
                "VALUES (:id, :code, 'Efectivo', 'CASH', false, 'ACTIVE', 'seed', 'seed', now(), now())"
            ),
            {"id": method_id, "code": code},
        )
    return str(method_id)


def _delete_fails(statement: str, **params) -> bool:
    try:
        with engine.begin() as connection:
            connection.execute(text(statement), params)
    except Exception as error:  # noqa: BLE001 — se comprueba el mensaje del trigger
        return "no se eliminan" in str(error)
    return False


def test_payment_methods_cannot_be_deleted_or_truncated_and_downgrade_restores_delete():
    """Spec 020 (FR-020-10, RC-MVP-4): sin borrado físico en la base; `downgrade` solo quita los triggers."""
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    method_id = _insert_method("PRUEBA")

    assert _delete_fails("DELETE FROM global_payment_methods WHERE id = :id", id=method_id)
    assert _delete_fails("TRUNCATE TABLE global_payment_methods")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM global_payment_methods")).scalar_one() == 1

    command.downgrade(config, "4a30e958088d")
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM global_payment_methods WHERE id = :id"), {"id": method_id})
    command.upgrade(config, "head")
