"""Ajustes manuales aplicados al registrarlos (FR-030 a FR-035; DS-04 a DS-06; research.md R-02, R-09).

Flujo (como R-03 (012), con el usuario humano como "cliente"):

1. Formato propio: `unit_cost` no se admite en un ajuste negativo.
2. Idempotencia por `adjustment_key` ligada al `sub` del usuario y a la huella de la
   solicitud: misma solicitud → el ajuste original **sin** llamar a dependencias.
3. Acceso: membresía y asignación `ACTIVE` a la sucursal con el token del usuario
   (`operational-access?branch_id=`); el usuario operativo sale de ahí (C-02).
4. Producto apto para movimientos (Commercial Relationship, identidad técnica) y,
   si el ajuste es positivo, moneda de la empresa.
5. Una operación `ADJUSTMENT` de 1 línea con el motor de la Fase A; el ajuste y su
   evento de auditoría se escriben en la misma transacción.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sio_audit.event import AuditEvent
from sio_audit.outbox import record_audit_event
from sqlalchemy.orm import Session

from inventory_service.application.branch_access import require_branch_access
from inventory_service.application.exceptions import (
    InventoryError,
    OperationKeyConflictError,
    ValidationFailedError,
    field_error,
)
from inventory_service.application.operation_service import Caller, log_rejection, resolve_existing
from inventory_service.application.ports import CompanyAccessDirectory
from inventory_service.application.reference_validation import ReferenceValidator
from inventory_service.domain.balance_math import ADJUSTMENT, NEGATIVE_ADJUSTMENT, ORIGIN_ADJUSTMENT, POSITIVE_ADJUSTMENT
from inventory_service.domain.canonical import request_hash
from inventory_service.domain.quantities import format_decimal, format_money
from inventory_service.infrastructure.repository import (
    AdjustmentQueries,
    AdjustmentRow,
    KeyTakenError,
    MovementRow,
    NewLine,
    NewOperation,
    SqlInventoryRepository,
    StoredOperation,
    adjustment_values,
    insert_adjustments,
)

MAX_KEY_ATTEMPTS = 3
ENTITY_TYPE = "InventoryAdjustment"


def keycloak_uuid(subject: str) -> UUID | None:
    """El `sub` de Keycloak es un UUID; si no lo es, el evento lo omite (sigue en `created_by`)."""
    try:
        return UUID(subject)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class AdjustmentResult:
    adjustment: AdjustmentRow
    movement: MovementRow
    created: bool


def adjustment_event(row: dict[str, Any], subject: str, request_id: UUID | None, correlation_id: UUID) -> AuditEvent:
    return AuditEvent(
        event_id=None,
        action="CREATE_INVENTORY_ADJUSTMENT",
        entity_type=ENTITY_TYPE,
        entity_id=row["id"],
        result="SUCCESS",
        occurred_at=row["created_at"],
        company_id=row["company_id"],
        branch_id=row["branch_id"],
        application_user_id=row["application_user_id"],
        keycloak_user_id=keycloak_uuid(subject),
        reason=row["reason"],
        request_id=request_id,
        correlation_id=correlation_id,
        new_values={
            "operation_id": str(row["operation_id"]),
            "movement_id": str(row["movement_id"]),
            "company_product_id": str(row["company_product_id"]),
            "adjustment_type": row["adjustment_type"],
            "quantity": format_decimal(row["quantity"]),
            "previous_balance": format_decimal(row["previous_balance"]),
            "new_balance": format_decimal(row["new_balance"]),
            "unit_cost": format_decimal(row["unit_cost"]),
            "adjustment_value": format_money(row["adjustment_value"]),
            "inventory_count_id": str(row["inventory_count_id"]) if row["inventory_count_id"] else None,
        },
    )


class AdjustmentService:
    def __init__(
        self,
        repository: SqlInventoryRepository,
        queries: AdjustmentQueries,
        validator: ReferenceValidator,
        access: CompanyAccessDirectory,
        *,
        request_id: Callable[[], UUID | None],
    ) -> None:
        self._repository = repository
        self._queries = queries
        self._validator = validator
        self._access = access
        self._request_id = request_id

    def register(self, company_id: UUID, data: Any, subject: str) -> AdjustmentResult:
        try:
            return self._register(company_id, data, subject)
        except InventoryError as error:
            log_rejection(data.adjustment_key, error)
            raise

    def _register(self, company_id: UUID, data: Any, subject: str) -> AdjustmentResult:
        positive = data.adjustment_type == "POSITIVE"
        if not positive and data.unit_cost is not None:
            raise ValidationFailedError(
                [field_error("unit_cost", "UNIT_COST_NOT_ALLOWED", "Un ajuste negativo toma su costo de las capas FIFO.")]
            )

        caller = Caller(subject=subject, client_id=subject)
        fingerprint = request_hash(
            {
                "company_id": company_id,
                "branch_id": data.branch_id,
                "company_product_id": data.company_product_id,
                "adjustment_type": data.adjustment_type,
                "quantity": data.quantity,
                "unit_cost": data.unit_cost,
                "reason": data.reason,
            },
            subject,
            ADJUSTMENT,
        )

        existing = self._existing(data.adjustment_key, caller, fingerprint)
        if existing is not None:
            return existing

        operator = require_branch_access(self._access, company_id, data.branch_id)
        errors = self._validator.validate_products(company_id, [("company_product_id", data.company_product_id)])
        currency = self._validator.company_currency(company_id, errors) if positive else None
        if errors:
            raise ValidationFailedError(errors)

        adjustment_id = uuid4()
        correlation_id = uuid4()
        operation = NewOperation(
            operation_key=data.adjustment_key,
            client_id=subject,
            created_by=subject,
            operation_type=ADJUSTMENT,
            company_id=company_id,
            branch_id=data.branch_id,
            origin_type=ORIGIN_ADJUSTMENT,
            origin_id=adjustment_id,
            application_user_id=operator.application_user_id,
            correlation_id=correlation_id,
            reason=data.reason,
            reverses_operation_id=None,
            request_hash=fingerprint,
            currency_code=currency,
            lines=[
                NewLine(
                    index=0,
                    origin_detail_id=adjustment_id,
                    company_product_id=data.company_product_id,
                    quantity=data.quantity,
                    unit_cost=data.unit_cost,
                    movement_type=POSITIVE_ADJUSTMENT if positive else NEGATIVE_ADJUSTMENT,
                    cost_field="unit_cost",
                )
            ],
        )

        def on_applied(session: Session, stored: StoredOperation) -> None:
            row = adjustment_values(
                adjustment_id,
                stored,
                stored.movements[0],
                reason=data.reason,
                application_user_id=operator.application_user_id,
            )
            insert_adjustments(session, [row])
            record_audit_event(session, adjustment_event(row, subject, self._request_id(), correlation_id))

        for _ in range(MAX_KEY_ATTEMPTS):
            try:
                stored = self._repository.apply_operation(operation, on_applied)
                adjustment, movement = self._queries.by_operation(stored.id)[0]
                return AdjustmentResult(adjustment, movement, created=True)
            except KeyTakenError:
                existing = self._existing(data.adjustment_key, caller, fingerprint)
                if existing is not None:
                    return existing

        raise OperationKeyConflictError()

    def _existing(self, key: UUID, caller: Caller, fingerprint: str) -> AdjustmentResult | None:
        stored = resolve_existing(self._repository, key, caller, fingerprint)
        if stored is None:
            return None
        pairs = self._queries.by_operation(stored.id)
        if stored.operation_type != ADJUSTMENT or stored.origin_type != ORIGIN_ADJUSTMENT or not pairs:
            raise OperationKeyConflictError()
        adjustment, movement = pairs[0]
        return AdjustmentResult(adjustment, movement, created=False)
