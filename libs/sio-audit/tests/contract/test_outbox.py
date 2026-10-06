"""Outbox transaccional del emisor (FR-077; RC-04; T051)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sio_audit.event import AuditEvent
from sio_audit.outbox import (
    InvalidAuditEventError,
    create_audit_outbox_table,
    drop_audit_outbox_table,
    record_audit_event,
)


def make_event(**changes) -> AuditEvent:
    values = {
        "event_id": uuid4(),
        "company_id": uuid4(),
        "action": "CREATE",
        "entity_type": "Purchase",
        "result": "SUCCESS",
        "occurred_at": datetime.now(UTC),
        "new_values": {"total": "10.00"},
    }
    values.update(changes)
    return AuditEvent(**values)


def rows(engine) -> list:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT event_id, payload, status, attempts, sent_at FROM audit_outbox")
        ).all()


def test_alembic_helpers_create_and_drop(outbox_engine) -> None:
    """El helper de migración crea y elimina la tabla con sus nombres (esquema aislado)."""
    with outbox_engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS sio_audit_migration_check CASCADE"))
        connection.execute(text("CREATE SCHEMA sio_audit_migration_check"))
        connection.execute(text("SET LOCAL search_path TO sio_audit_migration_check"))
        operations = Operations(MigrationContext.configure(connection))

        create_audit_outbox_table(operations)
        names = set(
            connection.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'sio_audit_migration_check.audit_outbox'::regclass"
                )
            ).scalars()
        )
        indexes = set(
            connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = 'sio_audit_migration_check' AND tablename = 'audit_outbox'"
                )
            ).scalars()
        )
        drop_audit_outbox_table(operations)
        exists = connection.execute(text("SELECT to_regclass('sio_audit_migration_check.audit_outbox')")).scalar()
        connection.execute(text("DROP SCHEMA sio_audit_migration_check CASCADE"))

    assert {
        "pk_audit_outbox",
        "ck_audit_outbox_status",
        "ck_audit_outbox_sent_at",
        "ck_audit_outbox_attempts_non_negative",
    } <= names
    assert "ix_audit_outbox_pending" in indexes
    assert exists is None


def test_record_in_committed_transaction(clean_outbox) -> None:
    event = make_event()
    with Session(clean_outbox) as session:
        returned = record_audit_event(session, event)
        session.commit()

    [row] = rows(clean_outbox)
    assert returned == event.event_id == row.event_id
    assert row.status == "PENDING" and row.attempts == 0 and row.sent_at is None
    assert row.payload["event_id"] == str(event.event_id)
    assert row.payload["occurred_at"].endswith("Z")


def test_rolled_back_transaction_leaves_no_event(clean_outbox) -> None:
    with Session(clean_outbox) as session:
        record_audit_event(session, make_event())
        session.rollback()

    assert rows(clean_outbox) == []


def test_event_id_assigned_when_missing(clean_outbox) -> None:
    with Session(clean_outbox) as session:
        returned = record_audit_event(session, make_event(event_id=None))
        session.commit()
    assert rows(clean_outbox)[0].event_id == returned


def test_invalid_event_raises_and_writes_nothing(clean_outbox) -> None:
    with Session(clean_outbox) as session:
        with pytest.raises(InvalidAuditEventError) as error:
            record_audit_event(session, make_event(action="no-valido"))
        session.commit()

    assert {item.field for item in error.value.errors} == {"action"}
    assert rows(clean_outbox) == []


def test_sensitive_values_never_reach_the_outbox(clean_outbox) -> None:
    secret = "valor-secreto-original"
    with Session(clean_outbox) as session:
        record_audit_event(
            session, make_event(new_values={"password": secret, "nested": [{"api_key": secret}]})
        )
        session.commit()

    [row] = rows(clean_outbox)
    assert secret not in json.dumps(row.payload)
    assert row.payload["new_values"] == {"password": "***", "nested": [{"api_key": "***"}]}
    assert row.payload["redacted_paths"] == ["new_values.nested[0].api_key", "new_values.password"]


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO audit_outbox (event_id, payload, status) VALUES (gen_random_uuid(), '{}', 'OTRO')",
        "INSERT INTO audit_outbox (event_id, payload, status) VALUES (gen_random_uuid(), '{}', 'SENT')",
        "INSERT INTO audit_outbox (event_id, payload, attempts) VALUES (gen_random_uuid(), '{}', -1)",
    ],
)
def test_constraints(clean_outbox, statement: str) -> None:
    with pytest.raises(IntegrityError):
        with clean_outbox.begin() as connection:
            connection.execute(text(statement))
