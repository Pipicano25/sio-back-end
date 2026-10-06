"""Eventos de auditoría de Inventory (FR-070 a FR-074; research.md R-11).

Un evento por operación aplicada y por reverso, escrito en `audit_outbox` con
`sio_audit.outbox.record_audit_event` **dentro de la transacción** de la operación:
si la transacción se revierte, el evento no existe. El `inventory-audit-outbox-worker`
lo entrega a Audit. Los rechazos no generan eventos (FR-074).
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sio_audit.event import AuditEvent
from sio_audit.outbox import record_audit_event
from sqlalchemy.orm import Session

from inventory_service.application.reference_validation import ValidatedReferences
from inventory_service.domain.balance_math import ENTRY, ENTRY_REVERSAL, OUTPUT, OUTPUT_REVERSAL
from inventory_service.domain.quantities import format_decimal
from inventory_service.infrastructure.repository import OnApplied, StoredOperation

ENTITY_TYPE = "InventoryOperation"

ACTION_BY_OPERATION = {
    ENTRY: "APPLY_INVENTORY_ENTRY",
    OUTPUT: "APPLY_INVENTORY_OUTPUT",
    ENTRY_REVERSAL: "REVERSE_INVENTORY_ENTRY",
    OUTPUT_REVERSAL: "REVERSE_INVENTORY_OUTPUT",
}


def build_event(stored: StoredOperation, references: ValidatedReferences, request_id: UUID | None) -> AuditEvent:
    return AuditEvent(
        event_id=None,
        action=ACTION_BY_OPERATION[stored.operation_type],
        entity_type=ENTITY_TYPE,
        entity_id=stored.id,
        result="SUCCESS",
        occurred_at=stored.created_at,
        company_id=stored.company_id,
        branch_id=stored.branch_id,
        application_user_id=stored.application_user_id,
        keycloak_user_id=references.keycloak_user_id,
        reason=stored.reason,
        request_id=request_id,
        correlation_id=stored.correlation_id,
        new_values={
            "operation_key": str(stored.operation_key),
            "operation_type": stored.operation_type,
            "origin_type": stored.origin_type,
            "origin_id": str(stored.origin_id),
            "reverses_operation_id": str(stored.reverses_operation_id) if stored.reverses_operation_id else None,
            "lines": [
                {
                    "origin_detail_id": str(movement.origin_detail_id),
                    "company_product_id": str(movement.company_product_id),
                    "quantity": format_decimal(movement.quantity),
                    "unit_cost": format_decimal(movement.unit_cost) if movement.unit_cost is not None else None,
                    "movement_id": str(movement.id),
                    "previous_balance": format_decimal(movement.previous_balance),
                    "new_balance": format_decimal(movement.new_balance),
                }
                for movement in stored.movements
            ],
        },
    )


def make_audit_hook(request_id: Callable[[], UUID | None]) -> Callable[[StoredOperation, ValidatedReferences], OnApplied]:
    """Gancho que registra el evento en la outbox dentro de la transacción en curso."""

    def hook(stored: StoredOperation, references: ValidatedReferences) -> OnApplied:
        def on_applied(session: Session, applied: StoredOperation) -> None:
            record_audit_event(session, build_event(applied, references, request_id()))

        return on_applied

    return hook
