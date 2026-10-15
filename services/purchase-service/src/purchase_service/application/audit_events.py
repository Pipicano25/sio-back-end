"""Eventos de auditoría de Purchase (FR-044; research.md R-13).

Un evento por acción, escrito en `audit_outbox` con `sio_audit.outbox.record_audit_event`
**dentro de la transacción** del cambio: si la transacción se revierte, el evento no
existe. El `purchase-audit-outbox-worker` lo entrega a Audit. Los rechazos previos a
cualquier efecto no generan eventos; un fallo de confirmación o anulación con operación
registrada genera el evento con `result = FAILURE`.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sio_audit.event import AuditEvent
from sio_audit.outbox import record_audit_event
from sqlalchemy.orm import Session

from purchase_service.observability import current_trace_id

PURCHASE = "Purchase"
PURCHASE_DETAIL = "PurchaseDetail"
LIFECYCLE_EVENT = "PurchaseLifecycleEvent"
SEQUENCE = "PurchaseSequence"

CREATE_PURCHASE = "CREATE_PURCHASE"
UPDATE_PURCHASE = "UPDATE_PURCHASE"
ADD_PURCHASE_DETAIL = "ADD_PURCHASE_DETAIL"
UPDATE_PURCHASE_DETAIL = "UPDATE_PURCHASE_DETAIL"
DELETE_PURCHASE_DETAIL = "DELETE_PURCHASE_DETAIL"
CONFIRM_PURCHASE = "CONFIRM_PURCHASE"
CANCEL_PURCHASE = "CANCEL_PURCHASE"
RECEIVE_PURCHASE = "RECEIVE_PURCHASE"
"""Spec 020: recepción física completa (entrada en Inventory)."""
RECORD_LIFECYCLE_EVENT = "RECORD_PURCHASE_LIFECYCLE_EVENT"
CREATE_SEQUENCE = "CREATE_PURCHASE_SEQUENCE"
UPDATE_SEQUENCE = "UPDATE_PURCHASE_SEQUENCE"
DEACTIVATE_SEQUENCE = "DEACTIVATE_PURCHASE_SEQUENCE"
REACTIVATE_SEQUENCE = "REACTIVATE_PURCHASE_SEQUENCE"

ACTIONS = (
    CREATE_PURCHASE,
    UPDATE_PURCHASE,
    ADD_PURCHASE_DETAIL,
    UPDATE_PURCHASE_DETAIL,
    DELETE_PURCHASE_DETAIL,
    CONFIRM_PURCHASE,
    CANCEL_PURCHASE,
    RECEIVE_PURCHASE,
    RECORD_LIFECYCLE_EVENT,
    CREATE_SEQUENCE,
    UPDATE_SEQUENCE,
    DEACTIVATE_SEQUENCE,
    REACTIVATE_SEQUENCE,
)


def _request_id() -> UUID | None:
    trace_id = current_trace_id()
    try:
        return UUID(hex=trace_id) if trace_id else None
    except ValueError:
        return None


def jsonable(values: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if values is None:
        return None
    result: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, Mapping):
            result[key] = jsonable(value)
        elif isinstance(value, list | tuple):
            result[key] = [jsonable(item) if isinstance(item, Mapping) else _scalar(item) for item in value]
        else:
            result[key] = _scalar(value)
    return result


def _scalar(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def record(
    session: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: UUID,
    company_id: UUID,
    branch_id: UUID | None,
    application_user_id: UUID | None,
    result: str = "SUCCESS",
    previous_values: Mapping[str, Any] | None = None,
    new_values: Mapping[str, Any] | None = None,
    reason: str | None = None,
    correlation_id: UUID | None = None,
    occurred_at: datetime | None = None,
) -> UUID:
    """Registra el evento en la outbox de la transacción en curso."""
    return record_audit_event(
        session,
        AuditEvent(
            event_id=None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            result=result,
            occurred_at=occurred_at or datetime.now(UTC),
            company_id=company_id,
            branch_id=branch_id,
            application_user_id=application_user_id,
            previous_values=jsonable(previous_values),
            new_values=jsonable(new_values),
            reason=reason,
            request_id=_request_id(),
            correlation_id=correlation_id,
        ),
    )
