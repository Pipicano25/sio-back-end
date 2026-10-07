"""Conciliador de operaciones `PENDING` (FR-025, DS-05, RC-06; research.md R-08).

Cada ciclo toma, con `FOR UPDATE SKIP LOCKED`, las operaciones `PENDING` cuyo
`updated_at` es anterior al umbral, les pone una **marca** (`updated_at` nuevo) y libera el
bloqueo; luego, por cada una, consulta Inventory **por clave** (nunca vuelve a aplicar):

- existe → completa como la solicitud original (número, `CONFIRMED` / `CANCELLED`, `SUCCEEDED`);
- no existe → `FAILED` `NOT_APPLIED_AFTER_RECONCILIATION`, solo si nadie tocó la operación
  desde la marca (un reintento del cliente la renueva antes de llamar a Inventory);
- Inventory no disponible → sin cambios hasta el siguiente ciclo;
- `COMPENSATION_PENDING` → reintenta el reverso compensatorio.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from purchase_service.application.exceptions import DependencyUnavailableError, OperationNotAppliedError, PurchaseError
from purchase_service.application.operation_engine import OperationEngine
from purchase_service.application.ports import InventoryGateway
from purchase_service.domain.status import CONFIRM, COMPENSATION_PENDING, PENDING, RECONCILER_ACTOR
from purchase_service.infrastructure.models import PurchaseOperation
from purchase_service.infrastructure.repository import PurchaseRepository
from purchase_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
BATCH = 50


@dataclass
class CycleResult:
    claimed: int = 0
    completed: list[UUID] = field(default_factory=list)
    failed: list[UUID] = field(default_factory=list)
    compensated: list[UUID] = field(default_factory=list)
    unchanged: list[UUID] = field(default_factory=list)


class ReconciliationService:
    def __init__(
        self,
        repository: PurchaseRepository,
        engine: OperationEngine,
        inventory: InventoryGateway,
        *,
        threshold_seconds: float,
    ) -> None:
        self._repo = repository
        self._engine = engine
        self._inventory = inventory
        self._threshold = threshold_seconds

    def run_once(self, limit: int = BATCH) -> CycleResult:
        result = CycleResult()
        try:
            claims = self._repo.claim_stale_pending(self._threshold, limit, RECONCILER_ACTOR)
            self._repo.commit()
        except Exception:
            self._repo.rollback()
            raise
        result.claimed = len(claims)

        for operation_id, marker in claims:
            try:
                self._process(operation_id, marker, result)
            except Exception:  # noqa: BLE001 — una operación no detiene el ciclo
                logger.exception("Error al conciliar la operación operacion=%s", operation_id)
                result.unchanged.append(operation_id)
        return result

    def _process(self, operation_id: UUID, marker: datetime, result: CycleResult) -> None:
        operation = self._repo.session.get(PurchaseOperation, operation_id, populate_existing=True)
        self._repo.end_read()
        if operation is None or operation.status != PENDING:
            result.unchanged.append(operation_id)
            return

        if operation.error_code == COMPENSATION_PENDING:
            try:
                self._engine.compensate(operation_id, RECONCILER_ACTOR)
            except PurchaseError:
                pass  # el resultado queda en la operación: FAILED si el reverso se aplicó, PENDING si no
            (result.compensated if self._status(operation_id) != PENDING else result.unchanged).append(operation_id)
            return

        try:
            found = self._inventory.find_by_key(operation.company_id, operation.id)
        except DependencyUnavailableError:
            logger.warning("Conciliación aplazada: Inventory no disponible operacion=%s", operation_id)
            result.unchanged.append(operation_id)
            return

        if found is None:
            if self._engine.fail(operation_id, OperationNotAppliedError(), RECONCILER_ACTOR, marker=marker):
                logger.warning("Operación cerrada por conciliación: no aplicada en Inventory operacion=%s", operation_id)
                result.failed.append(operation_id)
            else:
                result.unchanged.append(operation_id)
            return

        try:
            if operation.operation_type == CONFIRM:
                self._engine.complete_confirmation(operation_id, found.id, RECONCILER_ACTOR)
            else:
                self._engine.complete_cancellation(operation_id, found.id, RECONCILER_ACTOR)
        except PurchaseError:
            # Compensación iniciada o aplicada (número imposible): queda registrada en la operación.
            pass
        status = self._status(operation_id)
        (result.completed if status != PENDING else result.unchanged).append(operation_id)

    def _status(self, operation_id: UUID) -> str | None:
        operation = self._repo.session.get(PurchaseOperation, operation_id, populate_existing=True)
        status = operation.status if operation else None
        self._repo.end_read()
        return status
