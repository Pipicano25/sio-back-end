"""Utilidades de valores de auditoría (feature 016; research R-03; DS-05, DS-06, DS-09; T019).

Sin base de datos: el estado "cargado" se simula con `set_committed_value`, de modo que el
historial del ORM se comporta como tras `load_for_update`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from commercial_relationship_service.application import audit_events as audit
from commercial_relationship_service.audit_context import AuditActor, reset_actor, set_actor
from commercial_relationship_service.infrastructure.models import CompanyCustomerModel

ENTITY = "CompanyCustomer"
PLAIN_FIELD = "display_name"
PROTECTED_FIELD = None  # None si el servicio no protege campos


def loaded(**values) -> CompanyCustomerModel:
    model = CompanyCustomerModel()
    for key, value in values.items():
        set_committed_value(model, key, value)
    return model


def test_changes_keep_only_considered_fields_that_changed() -> None:
    model = loaded(id=uuid4(), **{PLAIN_FIELD: "Antes"}, version=1, updated_by="a")
    setattr(model, PLAIN_FIELD, "Después")
    model.version = 2
    model.updated_by = "b"

    assert audit.changes(model) == ({PLAIN_FIELD: "Antes"}, {PLAIN_FIELD: "Después"})


def test_same_value_or_only_technical_columns_is_not_a_change() -> None:
    model = loaded(id=uuid4(), **{PLAIN_FIELD: "Igual"}, version=1, updated_by="a")
    setattr(model, PLAIN_FIELD, "Igual")
    model.version = 2
    model.updated_by = "b"

    assert audit.changes(model) is None


def test_snapshot_excludes_technical_columns() -> None:
    model = loaded(id=uuid4(), **{PLAIN_FIELD: "Valor"}, version=3, created_by="x", updated_by="y")

    values = audit.snapshot(model)

    assert values[PLAIN_FIELD] == "Valor"
    assert not set(values) & audit.TECHNICAL_FIELDS


def test_jsonable_is_stable_for_uuid_decimal_and_dates() -> None:
    value = uuid4()
    when = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)

    assert audit.jsonable({"id": value, "amount": Decimal("10.50"), "at": when, "list": (1, value)}) == {
        "id": str(value), "amount": "10.50", "at": when.isoformat(), "list": [1, str(value)],
    }


@pytest.mark.skipif(PROTECTED_FIELD is None, reason="sin campos protegidos en este servicio")
def test_protected_fields_become_markers_and_are_declared() -> None:
    created = audit.protect(ENTITY, None, {PROTECTED_FIELD: "dato-sensible", PLAIN_FIELD: "visible"})
    assert created == (None, {PROTECTED_FIELD: audit.REGISTERED, PLAIN_FIELD: "visible"}, [f"new_values.{PROTECTED_FIELD}"])

    changed = audit.protect(ENTITY, {PROTECTED_FIELD: "antes"}, {PROTECTED_FIELD: "después"})
    assert changed == (
        {PROTECTED_FIELD: audit.MODIFIED},
        {PROTECTED_FIELD: audit.MODIFIED},
        [f"previous_values.{PROTECTED_FIELD}", f"new_values.{PROTECTED_FIELD}"],
    )

    removed = audit.protect(ENTITY, {PROTECTED_FIELD: "antes"}, {PROTECTED_FIELD: None})
    assert removed == ({PROTECTED_FIELD: audit.REMOVED}, {PROTECTED_FIELD: None}, [f"previous_values.{PROTECTED_FIELD}"])

    deleted = audit.protect(ENTITY, {PROTECTED_FIELD: "antes"}, None)
    assert deleted == ({PROTECTED_FIELD: audit.REMOVED}, None, [f"previous_values.{PROTECTED_FIELD}"])


@pytest.mark.skipif(PROTECTED_FIELD is None, reason="sin campos protegidos en este servicio")
def test_markers_never_carry_the_value_or_a_hash() -> None:
    previous, new, _ = audit.protect(ENTITY, {PROTECTED_FIELD: "secreto-1"}, {PROTECTED_FIELD: "secreto-2"})
    text = repr((previous, new))

    assert "secreto" not in text
    assert set(previous.values()) | set(new.values()) <= {audit.REGISTERED, audit.MODIFIED, audit.REMOVED, None}


def test_unprotected_fields_pass_through_with_their_value() -> None:
    values = {PLAIN_FIELD: "visible"}

    assert audit.protect(ENTITY, None, values) == (None, values, [])


def test_tracking_requires_an_authenticated_actor() -> None:
    session = Session()
    model = loaded(id=uuid4(), **{PLAIN_FIELD: "A"})
    setattr(model, PLAIN_FIELD, "B")

    assert audit.track_update(session, model, action="X", entity_type=ENTITY) is False
    assert not session.info.get(audit.PENDING_KEY)

    token = set_actor(AuditActor(str(uuid4()), "usuario.prueba"))
    try:
        assert audit.track_update(session, model, action="X", entity_type=ENTITY) is True
    finally:
        reset_actor(token)
    assert len(session.info[audit.PENDING_KEY]) == 1


def test_rollback_discards_pending_events() -> None:
    session = Session()
    model = loaded(id=uuid4(), **{PLAIN_FIELD: "A"})
    setattr(model, PLAIN_FIELD, "B")
    token = set_actor(AuditActor(str(uuid4()), "usuario.prueba"))
    try:
        assert audit.track_update(session, model, action="X", entity_type=ENTITY) is True
    finally:
        reset_actor(token)

    session.rollback()

    assert audit.PENDING_KEY not in session.info


def test_update_without_changes_tracks_nothing() -> None:
    session = Session()
    model = loaded(id=uuid4(), **{PLAIN_FIELD: "A"})
    setattr(model, PLAIN_FIELD, "A")
    token = set_actor(AuditActor(str(UUID(int=1)), "usuario.prueba"))
    try:
        assert audit.track_update(session, model, action="X", entity_type=ENTITY) is False
    finally:
        reset_actor(token)
    assert not session.info.get(audit.PENDING_KEY)
