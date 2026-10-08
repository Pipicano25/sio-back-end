"""Eventos de auditoría de Sales (FR-031; research.md R-13).

Los datos de los eventos nunca incluyen costo ni margen: Audit no aplica el permiso de
rentabilidad (DS-12).

Un evento por acción, escrito en `audit_outbox` con `sio_audit.outbox.record_audit_event`
**dentro de la transacción** del cambio: si la transacción se revierte, el evento no
existe. El `sales-audit-outbox-worker` lo entrega a Audit. Los rechazos previos a
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

from sales_service.observability import current_trace_id

SALE = "Sale"
SALE_DETAIL = "SaleDetail"
SEQUENCE = "SaleSequence"

CREATE_SALE = "CREATE_SALE"
UPDATE_SALE = "UPDATE_SALE"
ADD_SALE_DETAIL = "ADD_SALE_DETAIL"
UPDATE_SALE_DETAIL = "UPDATE_SALE_DETAIL"
DELETE_SALE_DETAIL = "DELETE_SALE_DETAIL"
CONFIRM_SALE = "CONFIRM_SALE"
CANCEL_SALE = "CANCEL_SALE"
CREATE_SEQUENCE = "CREATE_SALE_SEQUENCE"
UPDATE_SEQUENCE = "UPDATE_SALE_SEQUENCE"
DEACTIVATE_SEQUENCE = "DEACTIVATE_SALE_SEQUENCE"
REACTIVATE_SEQUENCE = "REACTIVATE_SALE_SEQUENCE"

ACTIONS = (
    CREATE_SALE,
    UPDATE_SALE,
    ADD_SALE_DETAIL,
    UPDATE_SALE_DETAIL,
    DELETE_SALE_DETAIL,
    CONFIRM_SALE,
    CANCEL_SALE,
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
