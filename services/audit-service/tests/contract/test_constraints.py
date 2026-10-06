"""Restricciones de `audit_events` declaradas en la base (Principio VIII; T011)."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

HASH = "a" * 64


def _row(**changes: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "event_id": str(uuid4()),
        "company_id": str(uuid4()),
        "branch_id": None,
        "username_snapshot": None,
        "action": "CREATE",
        "entity_type": "PriceList",
        "previous_values": None,
        "new_values": json.dumps({"code": "MIN"}),
        "result": "SUCCESS",
        "reason": None,
        "source_service": "audit-test-emitter",
        "content_hash": HASH,
        "created_by": "sub-sa",
        "updated_by": "sub-sa",
    }
    row.update(changes)
    return row


INSERT = text(
    """
    INSERT INTO audit_events (event_id, company_id, branch_id, username_snapshot, action, entity_type,
        previous_values, new_values, result, reason, source_service, occurred_at, content_hash,
        created_by, updated_by)
    VALUES (:event_id, :company_id, :branch_id, :username_snapshot, :action, :entity_type,
        CAST(:previous_values AS jsonb), CAST(:new_values AS jsonb), :result, :reason,
        :source_service, now(), :content_hash, :created_by, :updated_by)
    """
)


def _insert(engine, **changes: Any) -> None:
    with engine.begin() as connection:
        connection.execute(INSERT, _row(**changes))


def test_valid_row_and_defaults(test_engine, clean_database) -> None:
    _insert(test_engine)
    with test_engine.connect() as connection:
        row = connection.execute(
            text("SELECT id, redacted_paths, created_at = updated_at FROM audit_events")
        ).one()
    assert row[0] is not None
    assert row[1] == []
    assert row[2] is True


@pytest.mark.parametrize(
    ("changes", "constraint"),
    [
        ({"result": "OK"}, "ck_audit_events_result"),
        ({"action": "create"}, "ck_audit_events_action_format"),
        ({"entity_type": "price_list"}, "ck_audit_events_entity_type_format"),
        ({"company_id": None, "branch_id": str(uuid4())}, "ck_audit_events_branch_requires_company"),
        ({"new_values": json.dumps(["x"])}, "ck_audit_events_values_are_objects"),
        ({"previous_values": json.dumps("x")}, "ck_audit_events_values_are_objects"),
        ({"username_snapshot": "  "}, "ck_audit_events_texts_not_blank"),
        ({"reason": " con espacios "}, "ck_audit_events_texts_not_blank"),
        ({"reason": "r" * 2001}, "ck_audit_events_texts_not_blank"),
        ({"source_service": " "}, "ck_audit_events_texts_not_blank"),
        ({"content_hash": "Z" * 64}, "ck_audit_events_content_hash_format"),
        ({"updated_by": "otro"}, "ck_audit_events_audit_unchanged"),
    ],
)
def test_check_constraints(test_engine, clean_database, changes, constraint) -> None:
    with pytest.raises(IntegrityError) as error:
        _insert(test_engine, **changes)
    assert constraint in str(error.value)


def test_event_id_is_unique(test_engine, clean_database) -> None:
    event_id = str(uuid4())
    _insert(test_engine, event_id=event_id)

    with pytest.raises(IntegrityError) as error:
        _insert(test_engine, event_id=event_id)
    assert "uq_audit_events_event_id" in str(error.value)


def test_redacted_paths_not_null(test_engine, clean_database) -> None:
    with pytest.raises(IntegrityError):
        with test_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO audit_events (event_id, action, entity_type, result, source_service, "
                    "occurred_at, content_hash, created_by, updated_by, redacted_paths) VALUES "
                    "(gen_random_uuid(), 'CREATE', 'X', 'SUCCESS', 's', now(), :h, 'a', 'a', NULL)"
                ),
                {"h": HASH},
            )
