"""Reverso de una operación completa (FR-030 a FR-034; DS-06; research.md R-03, R-07).

- `company_id` es obligatorio: la operación original se busca **dentro de esa
  empresa** y del tipo de la ruta; si no existe ahí → `404` idéntico al de una
  operación inexistente (sin revelar operaciones de otras empresas).
- Un reverso no se revierte (`409 REVERSAL_NOT_ALLOWED`); una operación se revierte a
  lo sumo una vez (`409 ALREADY_REVERSED`, también bajo concurrencia por la
  restricción única `uq_inventory_operations_reverses`).
- No se vuelven a validar sucursal ni producto (inactivar no invalida documentos);
  el usuario operativo sí: existe y es de la empresa, aunque esté `INACTIVE`.
- Idempotente con su propia clave de reverso y huella (R-03).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from inventory_service.application.exceptions import (
    AlreadyReversedError,
    InventoryError,
    NotFoundError,
    ReversalNotAllowedError,
    ValidationFailedError,
    field_error,
)
from inventory_service.application.operation_service import (
    Caller,
    OperationResult,
    OperationService,
    log_rejection,
    resolve_existing,
)
from inventory_service.application.reference_validation import ValidatedReferences
from inventory_service.domain.balance_math import REVERSAL_OF, is_reversal
from inventory_service.domain.canonical import request_hash
from inventory_service.infrastructure.repository import NewLine, NewOperation


class ReversalService(OperationService):
    def reverse(self, original_type: str, operation_id: UUID, data: Any, caller: Caller) -> OperationResult:
        try:
            return self._reverse(original_type, operation_id, data, caller)
        except InventoryError as error:
            log_rejection(data.operation_key, error)
            raise

    def _reverse(self, original_type: str, operation_id: UUID, data: Any, caller: Caller) -> OperationResult:
        if data.reason is None:
            raise ValidationFailedError(
                [field_error("reason", "REASON_REQUIRED", "El motivo es obligatorio en un reverso.")]
            )

        reversal_type = REVERSAL_OF[original_type]
        payload = {
            "company_id": data.company_id,
            "reverses_operation_id": operation_id,
            "application_user_id": data.application_user_id,
            "correlation_id": data.correlation_id,
            "reason": data.reason,
        }
        fingerprint = request_hash(payload, caller.client_id, reversal_type)

        existing = resolve_existing(self._repository, data.operation_key, caller, fingerprint)
        if existing is not None:
            return OperationResult(existing, created=False)

        original = self._repository.get_operation(operation_id, data.company_id)

        if original is None or original.operation_type not in (original_type, reversal_type):
            raise NotFoundError()

        if is_reversal(original.operation_type):
            raise ReversalNotAllowedError()

        if original.reversed_by_operation_id is not None:
            raise AlreadyReversedError()

        keycloak_user_id = self._validator.validate_reversal_user(data.company_id, data.application_user_id)

        operation = NewOperation(
            operation_key=data.operation_key,
            client_id=caller.client_id,
            created_by=caller.subject,
            operation_type=reversal_type,
            company_id=original.company_id,
            branch_id=original.branch_id,
            origin_type=original.origin_type,
            origin_id=original.origin_id,
            application_user_id=data.application_user_id,
            correlation_id=data.correlation_id,
            reason=data.reason,
            reverses_operation_id=original.id,
            request_hash=fingerprint,
            lines=[
                NewLine(
                    index=movement.line_index,
                    origin_detail_id=movement.origin_detail_id,
                    company_product_id=movement.company_product_id,
                    quantity=movement.quantity,
                    unit_cost=movement.unit_cost,
                    reversed_movement_id=movement.id,
                )
                for movement in original.movements
            ],
        )
        return self._apply_with_key_race(
            operation, caller, fingerprint, ValidatedReferences(keycloak_user_id=keycloak_user_id)
        )
