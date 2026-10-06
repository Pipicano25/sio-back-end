"""Aplicación de entradas y salidas (FR-010 a FR-023; research.md R-03).

Flujo de R-03:

1. Validación de formato propia del tipo (origen, líneas repetidas, costo en salidas).
2. Idempotencia: si la clave existe, mismo cliente y misma huella → resultado
   original **sin** llamar a dependencias ni tocar saldos; si no → `409`.
3. Validación de referencias con sus dueños, fuera de la transacción (R-07).
4. Transacción del repositorio; si otra solicitud registró la clave primero se
   vuelve al paso 2 (nunca `500`).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from inventory_service.application.exceptions import (
    InventoryError,
    OperationKeyConflictError,
    ValidationFailedError,
    field_error,
)
from inventory_service.application.reference_validation import ReferenceValidator, ValidatedReferences
from inventory_service.domain.balance_math import OUTPUT, ORIGIN_TYPE_BY_OPERATION
from inventory_service.domain.canonical import request_hash
from inventory_service.infrastructure.repository import (
    KeyTakenError,
    NewLine,
    NewOperation,
    OnApplied,
    SqlInventoryRepository,
    StoredOperation,
)

MAX_KEY_ATTEMPTS = 3

logger = logging.getLogger("inventory_service")


def log_rejection(operation_key: UUID, error: InventoryError) -> None:
    """Los rechazos no se auditan (FR-074): solo quedan en el log, sin valores sensibles."""
    logger.info("Operación rechazada clave=%s codigo=%s", operation_key, error.code)


@dataclass(frozen=True, slots=True)
class Caller:
    """Cuenta de servicio que pide la operación (R-02)."""

    subject: str
    client_id: str


@dataclass(frozen=True, slots=True)
class OperationResult:
    stored: StoredOperation
    created: bool


AuditHook = Callable[[StoredOperation, ValidatedReferences], OnApplied]


def resolve_existing(
    repository: SqlInventoryRepository, operation_key: UUID, caller: Caller, fingerprint: str
) -> StoredOperation | None:
    """Paso 2 de R-03: resultado original o `409`; `None` si la clave no existe."""
    existing = repository.find_by_key(operation_key)

    if existing is None:
        return None

    if existing.requested_by_client != caller.client_id or existing.request_hash != fingerprint:
        raise OperationKeyConflictError()

    return existing


class OperationService:
    def __init__(
        self,
        repository: SqlInventoryRepository,
        validator: ReferenceValidator,
        *,
        audit_hook: AuditHook | None = None,
    ) -> None:
        self._repository = repository
        self._validator = validator
        self._audit_hook = audit_hook

    def apply(self, operation_type: str, data: Any, caller: Caller) -> OperationResult:
        try:
            return self._apply(operation_type, data, caller)
        except InventoryError as error:
            log_rejection(data.operation_key, error)
            raise

    def _apply(self, operation_type: str, data: Any, caller: Caller) -> OperationResult:
        self._check_format(operation_type, data)

        payload = {
            "company_id": data.company_id,
            "branch_id": data.branch_id,
            "origin_type": data.origin_type,
            "origin_id": data.origin_id,
            "application_user_id": data.application_user_id,
            "correlation_id": data.correlation_id,
            "reason": data.reason,
            "reverses_operation_id": None,
            "lines": [
                {
                    "origin_detail_id": item.origin_detail_id,
                    "company_product_id": item.company_product_id,
                    "quantity": item.quantity,
                    "unit_cost": item.unit_cost,
                }
                for item in data.lines
            ],
        }
        fingerprint = request_hash(payload, caller.client_id, operation_type)

        existing = resolve_existing(self._repository, data.operation_key, caller, fingerprint)
        if existing is not None:
            return OperationResult(existing, created=False)

        references = self._validator.validate_operation(
            data.company_id,
            data.branch_id,
            data.application_user_id,
            [item.company_product_id for item in data.lines],
        )

        operation = NewOperation(
            operation_key=data.operation_key,
            client_id=caller.client_id,
            created_by=caller.subject,
            operation_type=operation_type,
            company_id=data.company_id,
            branch_id=data.branch_id,
            origin_type=data.origin_type,
            origin_id=data.origin_id,
            application_user_id=data.application_user_id,
            correlation_id=data.correlation_id,
            reason=data.reason,
            reverses_operation_id=None,
            request_hash=fingerprint,
            lines=[
                NewLine(
                    index=index,
                    origin_detail_id=item.origin_detail_id,
                    company_product_id=item.company_product_id,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                )
                for index, item in enumerate(data.lines)
            ],
        )
        return self._apply_with_key_race(operation, caller, fingerprint, references)

    def _apply_with_key_race(
        self, operation: NewOperation, caller: Caller, fingerprint: str, references: ValidatedReferences
    ) -> OperationResult:
        for _ in range(MAX_KEY_ATTEMPTS):
            try:
                stored = self._repository.apply_operation(operation, self._on_applied(references))
                return OperationResult(stored, created=True)
            except KeyTakenError:
                # Otra solicitud con la misma clave confirmó primero: resultado original o `409`.
                existing = resolve_existing(self._repository, operation.operation_key, caller, fingerprint)
                if existing is not None:
                    return OperationResult(existing, created=False)

        raise OperationKeyConflictError()

    def _on_applied(self, references: ValidatedReferences) -> OnApplied | None:
        if self._audit_hook is None:
            return None
        return lambda session, stored: self._audit_hook(stored, references)(session, stored)

    @staticmethod
    def _check_format(operation_type: str, data: Any) -> None:
        errors: list[dict[str, str]] = []

        if data.origin_type != ORIGIN_TYPE_BY_OPERATION[operation_type]:
            errors.append(
                field_error(
                    "origin_type",
                    "ORIGIN_TYPE_MISMATCH",
                    f"El tipo de origen debe ser {ORIGIN_TYPE_BY_OPERATION[operation_type]}.",
                )
            )

        seen: set[UUID] = set()
        for index, item in enumerate(data.lines):
            if item.origin_detail_id in seen:
                errors.append(
                    field_error(
                        f"lines[{index}].origin_detail_id",
                        "DUPLICATE_ORIGIN_DETAIL",
                        "La línea de origen está repetida en la operación.",
                    )
                )
            seen.add(item.origin_detail_id)

            if operation_type == OUTPUT and item.unit_cost is not None:
                errors.append(
                    field_error(
                        f"lines[{index}].unit_cost",
                        "UNIT_COST_NOT_ALLOWED",
                        "Las salidas no aceptan costo unitario.",
                    )
                )

        if errors:
            raise ValidationFailedError(errors)
