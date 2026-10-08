"""Migración de la outbox de auditoría (feature 016; data-model.md; T014).

La revisión nueva crea `audit_outbox` con la estructura de `sio_audit.outbox`; `downgrade` a la
revisión previa la elimina y `upgrade` la vuelve a crear; los modelos y la base coinciden.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

import pytest
from alembic import command
from sio_audit.outbox import audit_outbox_table
from sqlalchemy import MetaData, create_engine, inspect

from tests.conftest import build_alembic_config

PREVIOUS_REVISION = "0018_widen_sector_name"
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


# Desviación previa a la 016 (registrada en validation-evidence.md): los índices de la Fase B
# (features 006/009) existen en la base por migración pero no se declaran en los modelos. La 016 no
# la corrige (no cambia Party Identity fuera de la auditoría); exige que la outbox no agregue otra.
PRE_EXISTING_INDEXES = {
    "ix_global_business_sectors_parent", "ix_global_business_sectors_status",
    "ix_organization_business_sectors_org", "ix_organization_contact_persons_org",
    "ix_organization_contact_profiles_confirmed_by_company", "ix_organization_contact_profiles_owner_valid_from",
    "ix_organization_legal_representatives_org", "ix_organization_legal_representatives_person",
    "ix_person_contact_profiles_confirmed_by_company", "ix_person_contact_profiles_owner_valid_from",
    "uq_organization_business_sectors_active", "uq_organization_business_sectors_primary",
    "uq_organization_contact_persons_person", "uq_organization_contact_persons_primary",
    "uq_organization_contact_profiles_active", "uq_organization_legal_representatives_person",
    "uq_organization_legal_representatives_primary", "uq_person_contact_profiles_active",
}


def test_models_and_database_match(test_database_url) -> None:
    from alembic.autogenerate import compare_metadata
    from alembic.runtime.migration import MigrationContext

    from party_identity_service.infrastructure import models  # noqa: F401
    from party_identity_service.infrastructure.database import Base

    engine = create_engine(test_database_url)
    try:
        with engine.connect() as connection:
            diffs = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()

    def pre_existing(diff) -> bool:
        if not isinstance(diff, tuple):
            return False
        if diff[0] == "remove_index":
            return diff[1].name in PRE_EXISTING_INDEXES
        # Única (classification_system, code) de sectores globales: también solo en la migración.
        return diff[0] == "remove_constraint" and diff[1].table.name == "global_business_sectors"

    unexpected = [diff for diff in diffs if not pre_existing(diff)]
    assert not unexpected, unexpected
