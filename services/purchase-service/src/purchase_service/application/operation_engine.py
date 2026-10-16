"""Finalización de operaciones distribuidas (research.md R-04, R-08, R-09; RC-01, RC-03, RC-06; spec 020).

Compra e Inventory están en bases distintas: no hay una transacción común. Cada
operación distribuida (`purchase_operations`) se registra `PENDING` **antes** de llamar a
Inventory y su `id` es la clave de operación enviada; el resultado se aplica después en una
transacción local corta. Lo usan la solicitud original, sus reintentos con la misma clave de
idempotencia y el conciliador; el bloqueo de la operación garantiza que a lo sumo uno la completa.

Spec 020: las operaciones distribuidas son la **recepción** (`RECEIVE`: entrada en Inventory,
FR-020-03) y la **anulación de una compra recibida** (`CANCEL`: reverso exacto de esa entrada).
La confirmación es local (`confirmation_service.py`) y numera antes de cualquier movimiento, así
que la recepción no puede fallar por numeración y no existe compensación (DS-03).

Orden de bloqueo: compra → operación.

El usuario operativo y el motivo de la solicitud original se guardan en columnas propias e
inmutables de la operación (`application_user_id`, `reason`; D-02): todo reintento y la
conciliación reenvían exactamente la misma solicitud. `error_details` solo guarda errores.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from purchase_service.application import audit_events as audit
from purchase_service.application.exceptions import (
    DependencyUnavailableError,
    InventoryAlreadyConsumedError,
    InventoryRejectedError,
    NotFoundError,
    PurchaseError,
    StoredError,
)
from purchase_service.application.ports import InventoryGateway, InventoryRejection
from purchase_service.application.purchase_service import PurchaseView
from purchase_service.application.price_update_delivery import record_price_update_facts
from purchase_service.application.snapshots import line_base_quantity, line_inventory_cost, touch
from purchase_service.domain.status import (
    CANCEL,
    CANCELLED,
    CONFIRMED,
    FAILED,
    PENDING,
    RECEIPT_RECEIVED,
    RECEIVE,
    SUCCEEDED,
)
from purchase_service.infrastructure.models import Purchase, PurchaseOperation
from purchase_service.infrastructure.repository import PurchaseRepository
from purchase_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

ORIGIN_TYPE = "PURCHASE"
ENTRY_LAYER_CONSUMED = "ENTRY_LAYER_CONSUMED"
ACTIONS = {RECEIVE: audit.RECEIVE_PURCHASE, CANCEL: audit.CANCEL_PURCHASE}


def stored_error(operation: PurchaseOperation) -> StoredError:
    details = operation.error_details or {}
    record = details.get("error") or {"code": operation.error_code, "message": "La operación falló."}
    return StoredError(record)


def map_rejection(rejection: InventoryRejection, operation_type: str) -> PurchaseError:
    if operation_type == CANCEL and rejection.code == ENTRY_LAYER_CONSUMED:
        return InventoryAlreadyConsumedError()
    logger.error(
        "Inventory rechazó la operación tipo=%s estado=%s codigo=%s", operation_type, rejection.status, rejection.code
    )
    return InventoryRejectedError(rejection.code, rejection.status)


class OperationEngine:
    def __init__(
        self,
        repository: PurchaseRepository,
        inventory: InventoryGateway,
        *,
        clock: Callable[[], datetime],
    ) -> None:
        self._repo = repository
        self._inventory = inventory
        self._clock = clock

    # ----------------------------------------------------------------- apoyo

    def _view(self, purchase: Purchase) -> PurchaseView:
        pending = self._repo.pending_operation(purchase.id)
        return PurchaseView(purchase, self._repo.lines(purchase.id), pending.id if pending else None)

    def _lock(self, operation_id: UUID) -> tuple[Purchase, PurchaseOperation]:
        """Bloquea compra y operación en el orden fijo (compra → operación)."""
        self._repo.begin()
        snapshot = self._repo.session.get(PurchaseOperation, operation_id, populate_existing=True)
        if snapshot is None:
            raise NotFoundError()
        purchase = self._repo.lock_purchase(snapshot.company_id, snapshot.purchase_id)
        operation = self._repo.lock_operation(operation_id)
        if purchase is None or operation is None:
            raise NotFoundError()
        return purchase, operation

    def finished(self, purchase: Purchase, operation: PurchaseOperation) -> PurchaseView:
        """Resultado de una operación ya terminada: la compra actual o el error original."""
        if operation.status == SUCCEEDED:
            return self._view(purchase)
        raise stored_error(operation)

    def load(self, operation_id: UUID) -> tuple[Purchase, PurchaseOperation]:
        operation = self._repo.session.get(PurchaseOperation, operation_id, populate_existing=True)
        if operation is None:
            raise NotFoundError()
        purchase = self._repo.get_purchase(operation.company_id, operation.purchase_id)
        if purchase is None:
            raise NotFoundError()
        return purchase, operation

    def claim(self, operation_id: UUID, actor: str) -> tuple[Purchase, PurchaseOperation] | PurchaseView:
        """Toma la operación para continuarla: marca `updated_at` (anula una marca del conciliador)."""
        try:
            purchase, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(purchase, operation)
            touch(operation, actor, self._clock())
            self._repo.flush()
            self._repo.commit()
            return purchase, operation
        except Exception:
            self._repo.rollback()
            raise

    # ------------------------------------------------------------- Inventory

    def entry_payload(self, purchase: Purchase, operation: PurchaseOperation, application_user_id: str) -> dict:
        """Solicitud de entrada, determinista a partir de lo congelado (la misma en todo reintento)."""
        lines = self._repo.lines(purchase.id)
        return {
            "operation_key": str(operation.id),
            "company_id": str(purchase.company_id),
            "branch_id": str(purchase.branch_id),
            "origin_type": ORIGIN_TYPE,
            "origin_id": str(purchase.id),
            "application_user_id": application_user_id,
            "correlation_id": str(operation.correlation_id),
            "reason": None,
            "lines": [
                {
                    "origin_detail_id": str(line.id),
                    "company_product_id": str(line.company_product_id),
                    "quantity": format(line_base_quantity(line), "f"),
                    "unit_cost": format(line_inventory_cost(line), "f"),
                }
                for line in lines
            ],
        }

    def run_receipt(self, operation_id: UUID, actor: str) -> PurchaseView:
        """Aplica en Inventory la entrada de la recepción con la clave de la operación (FR-020-03)."""
        claimed = self.claim(operation_id, actor)
        if isinstance(claimed, PurchaseView):
            return claimed
        purchase, operation = claimed
        payload = self.entry_payload(purchase, operation, str(operation.application_user_id))
        self._repo.end_read()

        try:
            reference = self._inventory.apply_entry(payload)
        except InventoryRejection as rejection:
            error = map_rejection(rejection, RECEIVE)
            self.fail(operation_id, error, actor)
            raise error from None
        except DependencyUnavailableError as error:
            error.context["operation_id"] = str(operation_id)
            raise

        return self.complete_receipt(operation_id, reference.id, actor)

    def complete_receipt(self, operation_id: UUID, inventory_operation_id: UUID, actor: str) -> PurchaseView:
        """Transacción T2: la compra queda recibida (una sola vez) con la entrada aplicada, todo o nada."""
        try:
            purchase, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(purchase, operation)
            if purchase.status != CONFIRMED or purchase.inventory_operation_id is not None:
                raise RuntimeError(f"Compra {purchase.id} en {purchase.status} con recepción pendiente")
            now = self._clock()
            purchase.inventory_operation_id = inventory_operation_id
            purchase.received_at = operation.started_at  # el momento en que el usuario confirmó la recepción
            purchase.received_by_user_id = operation.application_user_id
            touch(purchase, actor, now)
            operation.status = SUCCEEDED
            operation.inventory_operation_id = inventory_operation_id
            operation.completed_at = now
            touch(operation, actor, now)
            self._repo.flush()
            # Spec 021 (FR-021-14): serie de costos y solicitudes de precio en la misma T2 (outbox, EXC-001).
            record_price_update_facts(self._repo, purchase, self._repo.lines(purchase.id), actor, now)
            audit.record(
                self._repo.session,
                action=audit.RECEIVE_PURCHASE,
                entity_type=audit.PURCHASE,
                entity_id=purchase.id,
                company_id=purchase.company_id,
                branch_id=purchase.branch_id,
                application_user_id=operation.application_user_id,
                correlation_id=operation.correlation_id,
                previous_values={"receipt_status": "PENDING"},
                new_values={
                    "receipt_status": RECEIPT_RECEIVED,
                    "number": purchase.number,
                    "received_at": purchase.received_at,
                    "received_by_user_id": purchase.received_by_user_id,
                    "inventory_operation_id": inventory_operation_id,
                    "operation_id": operation.id,
                },
            )
            self._repo.commit()
            return PurchaseView(purchase, self._repo.lines(purchase.id), None)
        except Exception:
            self._repo.rollback()
            raise

    # ------------------------------------------------------------------ fallo

    def fail(
        self,
        operation_id: UUID,
        error: PurchaseError,
        actor: str,
        *,
        marker: datetime | None = None,
    ) -> bool:
        """Cierra la operación `FAILED` con el error; con `marker`, solo si nadie la tocó desde la marca."""
        try:
            purchase, operation = self._lock(operation_id)
            if operation.status != PENDING or (marker is not None and operation.updated_at != marker):
                self._repo.commit()
                return False
            now = self._clock()
            operation.status = FAILED
            operation.error_code = error.code
            operation.error_details = {"error": error.to_record()}
            operation.completed_at = now
            touch(operation, actor, now)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=ACTIONS.get(operation.operation_type, audit.CONFIRM_PURCHASE),
                entity_type=audit.PURCHASE,
                entity_id=purchase.id,
                company_id=purchase.company_id,
                branch_id=purchase.branch_id,
                application_user_id=operation.application_user_id,
                correlation_id=operation.correlation_id,
                result="FAILURE",
                reason=error.message[:2000],
                new_values={"operation_id": operation.id, "error_code": error.code},
            )
            self._repo.commit()
            return True
        except Exception:
            self._repo.rollback()
            raise

    # -------------------------------------------------------------- anulación

    def run_cancellation(self, operation_id: UUID, actor: str) -> PurchaseView:
        """Compra recibida: pide a Inventory el reverso exacto de su entrada y aplica el resultado (R-09)."""
        claimed = self.claim(operation_id, actor)
        if isinstance(claimed, PurchaseView):
            return claimed
        purchase, operation = claimed
        payload = {
            "operation_key": str(operation.id),
            "company_id": str(purchase.company_id),
            "application_user_id": str(operation.application_user_id),
            "correlation_id": str(operation.correlation_id),
            "reason": operation.reason,
        }
        entry_id = purchase.inventory_operation_id
        self._repo.end_read()

        try:
            reversal = self._inventory.reverse_entry(entry_id, payload)
        except InventoryRejection as rejection:
            error = map_rejection(rejection, CANCEL)
            self.fail(operation_id, error, actor)
            raise error from None
        except DependencyUnavailableError as error:
            error.context["operation_id"] = str(operation_id)
            raise

        return self.complete_cancellation(operation_id, reversal.id, actor)

    def complete_cancellation(self, operation_id: UUID, reversal_id: UUID, actor: str) -> PurchaseView:
        try:
            purchase, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(purchase, operation)
            if purchase.status != CONFIRMED:
                raise RuntimeError(f"Compra {purchase.id} en {purchase.status} con anulación pendiente")
            now = self._clock()
            purchase.status = CANCELLED
            purchase.cancelled_by_user_id = operation.application_user_id
            purchase.cancelled_at = now
            purchase.cancellation_reason = operation.reason
            touch(purchase, actor, now)
            operation.status = SUCCEEDED
            operation.inventory_operation_id = reversal_id
            operation.completed_at = now
            touch(operation, actor, now)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.CANCEL_PURCHASE,
                entity_type=audit.PURCHASE,
                entity_id=purchase.id,
                company_id=purchase.company_id,
                branch_id=purchase.branch_id,
                application_user_id=purchase.cancelled_by_user_id,
                correlation_id=operation.correlation_id,
                reason=purchase.cancellation_reason,
                previous_values={"status": CONFIRMED},
                new_values={
                    "status": CANCELLED,
                    "number": purchase.number,
                    "inventory_operation_id": purchase.inventory_operation_id,
                    "reversal_operation_id": reversal_id,
                    "operation_id": operation.id,
                },
            )
            self._repo.commit()
            return PurchaseView(purchase, self._repo.lines(purchase.id), None)
        except Exception:
            self._repo.rollback()
            raise
