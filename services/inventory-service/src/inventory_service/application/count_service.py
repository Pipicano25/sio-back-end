"""Conteos físicos (FR-040 a FR-045; DS-07 a DS-09; RC-13; research.md R-10, R-11).

- Crear (`DRAFT`), iniciar (`IN_PROGRESS`), registrar detalles, completar o cancelar.
  Toda operación exige usuario humano con membresía y asignación `ACTIVE` a la
  sucursal del conteo (R-09); el usuario operativo sale de `operational-access`.
- Completar aplica **una** operación `ADJUSTMENT` con origen `COUNT` y una línea por
  diferencia distinta de cero sobre el saldo vigente (DS-09), crea un ajuste por
  línea y cierra el conteo en una transacción (todo o nada).
- Idempotencia de la finalización por `completion_key` ligada al usuario y a la
  huella (`count_id`, `version`). Un conteo sin diferencias se completa sin
  operación; repetir esa finalización con la misma versión devuelve el conteo.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sio_audit.event import AuditEvent
from sio_audit.outbox import record_audit_event
from sqlalchemy.orm import Session

from inventory_service.application.adjustment_service import keycloak_uuid
from inventory_service.application.branch_access import OperatorAccess, require_branch_access
from inventory_service.application.exceptions import (
    InventoryError,
    NotFoundError,
    OperationKeyConflictError,
    ValidationFailedError,
)
from inventory_service.application.operation_service import Caller, log_rejection, resolve_existing
from inventory_service.application.ports import CompanyAccessDirectory
from inventory_service.application.reference_validation import ReferenceValidator
from inventory_service.domain.balance_math import (
    ADJUSTMENT,
    NEGATIVE_ADJUSTMENT,
    ORIGIN_COUNT,
    POSITIVE_ADJUSTMENT,
)
from inventory_service.domain.canonical import request_hash
from inventory_service.domain.quantities import format_decimal, format_money
from inventory_service.infrastructure.repository import (
    COUNT_ADJUSTMENT_REASON,
    AdjustmentQueries,
    CountDetailRow,
    CountRow,
    KeyTakenError,
    NewLine,
    NewOperation,
    SqlCountRepository,
    SqlInventoryRepository,
    StoredOperation,
)

ENTITY_TYPE = "InventoryCount"
MAX_KEY_ATTEMPTS = 3
ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class CountView:
    count: CountRow
    details: list[CountDetailRow]
    adjustments: list[Any]


class CountService:
    def __init__(
        self,
        counts: SqlCountRepository,
        engine: SqlInventoryRepository,
        adjustments: AdjustmentQueries,
        validator: ReferenceValidator,
        access: CompanyAccessDirectory,
        *,
        request_id: Callable[[], UUID | None],
    ) -> None:
        self._counts = counts
        self._engine = engine
        self._adjustments = adjustments
        self._validator = validator
        self._access = access
        self._request_id = request_id

    # Lectura ------------------------------------------------------------------------

    def list(self, company_id: UUID, **filters: Any):
        return self._counts.list(company_id, **filters)

    def view(self, company_id: UUID, count_id: UUID) -> CountView:
        count = self._load(company_id, count_id)
        return self._view(count)

    def _view(self, count: CountRow) -> CountView:
        adjustments = self._adjustments.by_count(count.id) if count.status == "COMPLETED" else []
        return CountView(count, self._counts.details(count.id), adjustments)

    def _load(self, company_id: UUID, count_id: UUID) -> CountRow:
        count = self._counts.get(company_id, count_id)
        if count is None:
            raise NotFoundError()
        return count

    def _operator(self, count: CountRow) -> OperatorAccess:
        return require_branch_access(self._access, count.company_id, count.branch_id)

    # Escritura ----------------------------------------------------------------------

    def create(self, company_id: UUID, data: Any, subject: str) -> CountView:
        operator = require_branch_access(self._access, company_id, data.branch_id)
        count = self._counts.create(company_id, data.branch_id, operator.application_user_id, data.observations, subject)
        return CountView(count, [], [])

    def start(self, company_id: UUID, count_id: UUID, data: Any, subject: str) -> CountView:
        operator = self._operator(self._load(company_id, count_id))
        count = self._counts.start(
            company_id, count_id, data.version, subject, self._event_hook("START_INVENTORY_COUNT", operator, subject)
        )
        return self._view(count)

    def cancel(self, company_id: UUID, count_id: UUID, data: Any, subject: str) -> CountView:
        operator = self._operator(self._load(company_id, count_id))
        count = self._counts.cancel(
            company_id,
            count_id,
            data.version,
            data.reason,
            operator.application_user_id,
            subject,
            self._event_hook("CANCEL_INVENTORY_COUNT", operator, subject, reason=data.reason),
        )
        return self._view(count)

    def register_detail(self, company_id: UUID, count_id: UUID, product_id: UUID, data: Any, subject: str) -> CountDetailRow:
        operator = self._operator(self._load(company_id, count_id))
        errors = self._validator.validate_products(company_id, [("company_product_id", product_id)])
        if errors:
            raise ValidationFailedError(errors)
        return self._counts.register_detail(
            company_id, count_id, product_id, data.counted_quantity, data.unit_cost, operator.application_user_id, subject
        )

    def complete(self, company_id: UUID, count_id: UUID, data: Any, subject: str) -> CountView:
        try:
            return self._complete(company_id, count_id, data, subject)
        except InventoryError as error:
            log_rejection(data.completion_key, error)
            raise

    def _complete(self, company_id: UUID, count_id: UUID, data: Any, subject: str) -> CountView:
        caller = Caller(subject=subject, client_id=subject)
        fingerprint = request_hash(
            {"company_id": company_id, "count_id": count_id, "version": data.version}, subject, ADJUSTMENT
        )
        existing = self._existing(company_id, count_id, data.completion_key, caller, fingerprint)
        if existing is not None:
            return existing

        count = self._load(company_id, count_id)
        if count.status == "COMPLETED" and count.operation_id is None and data.version == count.version - 1:
            return self._view(count)  # reintento de un conteo completado sin diferencias

        operator = self._operator(count)
        errors: list[dict[str, str]] = []
        currency = self._validator.company_currency(company_id, errors)
        if errors:
            raise ValidationFailedError(errors)

        def build(locked: CountRow, details: list[CountDetailRow]) -> NewOperation | None:
            lines = []
            for detail in details:
                if detail.difference_quantity == ZERO:
                    continue
                surplus = detail.difference_quantity > ZERO
                lines.append(
                    NewLine(
                        index=len(lines),
                        origin_detail_id=detail.id,
                        company_product_id=detail.company_product_id,
                        quantity=abs(detail.difference_quantity),
                        unit_cost=detail.unit_cost if surplus else None,
                        movement_type=POSITIVE_ADJUSTMENT if surplus else NEGATIVE_ADJUSTMENT,
                        cost_field=f"details[{detail.company_product_id}].unit_cost",
                    )
                )
            if not lines:
                return None
            return NewOperation(
                operation_key=data.completion_key,
                client_id=subject,
                created_by=subject,
                operation_type=ADJUSTMENT,
                company_id=company_id,
                branch_id=locked.branch_id,
                origin_type=ORIGIN_COUNT,
                origin_id=locked.id,
                application_user_id=operator.application_user_id,
                correlation_id=locked.id,
                reason=COUNT_ADJUSTMENT_REASON,
                reverses_operation_id=None,
                request_hash=fingerprint,
                currency_code=currency,
                lines=lines,
            )

        def hook(session: Session, row: CountRow, stored: StoredOperation | None, adjustments: list[dict[str, Any]]) -> None:
            record_audit_event(session, self._completion_event(row, stored, adjustments, operator, subject))

        for _ in range(MAX_KEY_ATTEMPTS):
            try:
                row, _stored = self._counts.complete(
                    company_id, count_id, data.version, operator.application_user_id, subject, build, hook
                )
                return self._view(row)
            except KeyTakenError:
                existing = self._existing(company_id, count_id, data.completion_key, caller, fingerprint)
                if existing is not None:
                    return existing
        raise OperationKeyConflictError()

    def _existing(
        self, company_id: UUID, count_id: UUID, key: UUID, caller: Caller, fingerprint: str
    ) -> CountView | None:
        stored = resolve_existing(self._engine, key, caller, fingerprint)
        if stored is None:
            return None
        if stored.origin_type != ORIGIN_COUNT or stored.origin_id != count_id or stored.company_id != company_id:
            raise OperationKeyConflictError()
        return self._view(self._load(company_id, count_id))

    # Auditoría (R-11) ------------------------------------------------------------------

    def _event(
        self, action: str, row: CountRow, operator: OperatorAccess, subject: str, *, reason: str | None = None, values=None
    ) -> AuditEvent:
        return AuditEvent(
            event_id=None,
            action=action,
            entity_type=ENTITY_TYPE,
            entity_id=row.id,
            result="SUCCESS",
            occurred_at=row.updated_at,
            company_id=row.company_id,
            branch_id=row.branch_id,
            application_user_id=operator.application_user_id,
            keycloak_user_id=keycloak_uuid(subject),
            reason=reason,
            request_id=self._request_id(),
            correlation_id=row.id,
            new_values=values or {"status": row.status, "version": row.version},
        )

    def _event_hook(self, action: str, operator: OperatorAccess, subject: str, *, reason: str | None = None):
        def hook(session: Session, row: CountRow) -> None:
            record_audit_event(session, self._event(action, row, operator, subject, reason=reason))

        return hook

    def _completion_event(
        self,
        row: CountRow,
        stored: StoredOperation | None,
        adjustments: list[dict[str, Any]],
        operator: OperatorAccess,
        subject: str,
    ) -> AuditEvent:
        """Resumen (no el detalle): con 1 000 productos el evento sigue bajo 64 KB (R-11)."""
        positive = [item for item in adjustments if item["adjustment_type"] == "POSITIVE"]
        negative = [item for item in adjustments if item["adjustment_type"] == "NEGATIVE"]

        def total(items, key):
            return sum((item[key] for item in items), Decimal(0))

        values = {
            "count_id": str(row.id),
            "status": row.status,
            "version": row.version,
            "operation_id": str(stored.id) if stored is not None else None,
            "adjustments": len(adjustments),
            "positive_quantity": format_decimal(total(positive, "quantity")),
            "negative_quantity": format_decimal(total(negative, "quantity")),
            "positive_value": format_money(total(positive, "adjustment_value")),
            "negative_value": format_money(total(negative, "adjustment_value")),
        }
        return self._event("COMPLETE_INVENTORY_COUNT", row, operator, subject, values=values)
