"""Repositorio: inserción idempotente con `ON CONFLICT` y comparación de huella (T028)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from audit_service.application.ports import NewAuditEventRow
from audit_service.infrastructure.repository import SqlAlchemyAuditEventRepository


def _row(event_id, content_hash: str) -> NewAuditEventRow:
    return NewAuditEventRow(
        event_id=event_id,
        content_hash=content_hash,
        values={
            "event_id": event_id,
            "action": "CREATE",
            "entity_type": "PriceList",
            "result": "SUCCESS",
            "occurred_at": datetime.now(UTC),
            "source_service": "audit-test-emitter",
            "content_hash": content_hash,
            "created_by": "sub-sa",
            "updated_by": "sub-sa",
            "redacted_paths": [],
        },
    )


def test_insert_then_get_existing(test_engine, clean_database) -> None:
    event_id = uuid4()

    with Session(test_engine) as session:
        repo = SqlAlchemyAuditEventRepository(session)
        [created] = repo.insert_or_get([_row(event_id, "a" * 64)])
        repo.commit()
        assert created.created and not created.conflict
        created_id = created.row.id
        assert created_id is not None

    with Session(test_engine) as session:
        repo = SqlAlchemyAuditEventRepository(session)
        same, other = repo.insert_or_get([_row(event_id, "a" * 64), _row(event_id, "b" * 64)])
        same_id = same.row.id
        repo.rollback()

    assert not same.created and not same.conflict and same_id == created_id
    assert not other.created and other.conflict


def test_database_now_is_aware(test_engine, clean_database) -> None:
    with Session(test_engine) as session:
        assert SqlAlchemyAuditEventRepository(session).database_now().tzinfo is not None
