"""Migración de la outbox de auditoría (feature 016; data-model.md; T014).

La revisión nueva crea `audit_outbox` con la estructura de `sio_audit.outbox`; `downgrade` a la
revisión previa la elimina y `upgrade` la vuelve a crear; los modelos y la base coinciden.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

import pytest
from alembic import command
from alembic.util.exc import CommandError
from sio_audit.outbox import audit_outbox_table
from sqlalchemy import MetaData, create_engine, inspect

from tests.conftest import build_alembic_config

PREVIOUS_REVISION = "0002"
pytestmark = pytest.mark.usefixtures("migrated_database")


@contextmanager
def _database(url: str):
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        yield build_alembic_config()
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


def _outbox_columns(url: str) -> dict[str, str] | None:
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        if "audit_outbox" not in inspector.get_table_names():
            return None
        return {column["name"]: str(column["type"]) for column in inspector.get_columns("audit_outbox")}
    finally:
        engine.dispose()


def test_outbox_matches_the_shared_library(test_database_url) -> None:
    expected = audit_outbox_table(MetaData())
    columns = _outbox_columns(test_database_url)

    assert columns is not None
    assert set(columns) == {column.name for column in expected.columns}


def test_downgrade_and_upgrade_again(test_database_url) -> None:
    with _database(test_database_url) as config:
        command.downgrade(config, PREVIOUS_REVISION)
        assert _outbox_columns(test_database_url) is None
        command.upgrade(config, "head")
    assert _outbox_columns(test_database_url) is not None


def test_models_and_database_match(test_database_url) -> None:
    with _database(test_database_url) as config:
        try:
            command.check(config)
        except CommandError as error:  # pragma: no cover - el mensaje lista las diferencias
            pytest.fail(f"Modelos y base difieren: {error}")
