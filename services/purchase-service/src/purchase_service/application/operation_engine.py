"""Finalización de operaciones distribuidas (research.md R-04, R-05, R-08, R-09; RC-01, RC-03, RC-06).

Compra e Inventory están en bases distintas: no hay una transacción común. Cada
operación (`purchase_operations`) se registra `PENDING` **antes** de llamar a Inventory
y su `id` es la clave de operación enviada; el resultado se aplica después en una
transacción local corta. Lo usan la solicitud original, sus reintentos con la misma
clave de idempotencia y el conciliador; el bloqueo de la operación garantiza que a lo
sumo uno la completa.

Orden de bloqueo: compra → operación → contador de secuencia.

Compensación (R-05 paso 6): si Inventory aplicó la entrada pero la compra no puede
quedar `CONFIRMED` por una causa definitiva de numeración (sin secuencia, agotada o
número ya usado), se registra `COMPENSATION_PENDING` con el `inventory_operation_id` de
la entrada y se pide su reverso con una clave derivada y como usuario operativo el que
inició la confirmación (`application_user_id` de la operación, inmutable; D-07).

El usuario operativo y el motivo de la solicitud original se guardan en columnas propias e
inmutables de la operación (`application_user_id`, `reason`; D-02): todo reintento y la
conciliación reenvían exactamente la misma solicitud. `error_details` solo guarda errores. Si el reverso no puede
aplicarse, la operación **sigue `PENDING`**, visible y reconciliable: el conciliador lo
reintenta. Nunca se consume un número sin confirmar la compra (el contador se asigna en
la misma transacción que la confirma).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.exc import IntegrityError

from purchase_service.application import audit_events as audit
from purchase_service.application.exceptions import (
    DependencyUnavailableError,
    InventoryAlreadyConsumedError,
    InventoryRejectedError,
    NotFoundError,
    PurchaseError,
    SequenceExhaustedError,
    SequenceInUseError,
    SequenceNotConfiguredError,
    StoredError,
)
from purchase_service.application.ports import InventoryGateway, InventoryRejection
from purchase_service.application.purchase_service import PurchaseView
from purchase_service.application.snapshots import line_base_quantity, line_inventory_cost, touch
from purchase_service.domain.numbering import exceeds_maximum, format_number, period_key
from purchase_service.domain.status import (
    CANCEL,
    CANCELLED,
    COMPENSATION_PENDING,
    CONFIRM,
    CONFIRMED,
    DRAFT,
    FAILED,
    PENDING,
    SUCCEEDED,
)
from purchase_service.infrastructure.models import Purchase, PurchaseOperation
from purchase_service.infrastructure.repository import PurchaseRepository, violated_constraint
from purchase_service.infrastructure.sequence_repository import SequenceRepository
from purchase_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

UQ_NUMBER = "uq_purchases_company_number"
ORIGIN_TYPE = "PURCHASE"
COMPENSATION_NAMESPACE = uuid5(NAMESPACE_URL, "sio:purchase-service:compensation")
ENTRY_LAYER_CONSUMED = "ENTRY_LAYER_CONSUMED"


def compensation_key(operation_id: UUID) -> UUID:
    """Clave estable del reverso compensatorio de una confirmación (misma en todo reintento)."""
    return uuid5(COMPENSATION_NAMESPACE, str(operation_id))


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
        sequences: SequenceRepository,
        inventory: InventoryGateway,
        *,
        clock: Callable[[], datetime],
    ) -> None:
        self._repo = repository
        self._sequences = sequences
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

    def run_confirmation(self, operation_id: UUID, actor: str) -> PurchaseView:
        """Llama a Inventory con la clave de la operación y aplica el resultado (R-05 pasos 4–6)."""
        claimed = self.claim(operation_id, actor)
        if isinstance(claimed, PurchaseView):
            return claimed
        purchase, operation = claimed

        if operation.error_code == COMPENSATION_PENDING:
            return self.compensate(operation_id, actor)

        payload = self.entry_payload(purchase, operation, str(operation.application_user_id))
        self._repo.end_read()

        try:
            reference = self._inventory.apply_entry(payload)
        except InventoryRejection as rejection:
            error = map_rejection(rejection, CONFIRM)
            self.fail(operation_id, error, actor)
            raise error from None
        except DependencyUnavailableError as error:
            error.context["operation_id"] = str(operation_id)
            raise

        return self.complete_confirmation(operation_id, reference.id, actor)

    def complete_confirmation(
        self, operation_id: UUID, inventory_operation_id: UUID, actor: str
    ) -> PurchaseView:
        """Transacción T2: número del período, `CONFIRMED`, `SUCCEEDED` y auditoría, todo o nada."""
        try:
            purchase, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(purchase, operation)
            if operation.error_code == COMPENSATION_PENDING:
                self._repo.commit()
                return self.compensate(operation_id, actor)
            if purchase.status != DRAFT:
                raise RuntimeError(f"Compra {purchase.id} en {purchase.status} con confirmación pendiente")

            sequence = self._sequences.applicable(purchase.company_id, purchase.branch_id)
            if sequence is None:
                raise SequenceNotConfiguredError()
            period = period_key(sequence.reset_policy, purchase.operation_date)
            value = self._sequences.assign(sequence, period, actor)
            if exceeds_maximum(value, sequence.maximum_number, sequence.number_length):
                raise SequenceExhaustedError(period)

            now = self._clock()
            purchase.number = format_number(sequence.prefix, sequence.separator, period, value, sequence.number_length)
            purchase.sequence_value = value
            purchase.purchase_sequence_id = sequence.id
            purchase.inventory_operation_id = inventory_operation_id
            purchase.status = CONFIRMED
            touch(purchase, actor, now)
            operation.status = SUCCEEDED
            operation.inventory_operation_id = inventory_operation_id
            operation.completed_at = now
            operation.error_code = None
            operation.error_details = None
            touch(operation, actor, now)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.CONFIRM_PURCHASE,
                entity_type=audit.PURCHASE,
                entity_id=purchase.id,
                company_id=purchase.company_id,
                branch_id=purchase.branch_id,
                application_user_id=operation.application_user_id,
                correlation_id=operation.correlation_id,
                previous_values={"status": DRAFT},
                new_values={
                    "status": CONFIRMED,
                    "number": purchase.number,
                    "sequence_value": value,
                    "purchase_sequence_id": sequence.id,
                    "inventory_operation_id": inventory_operation_id,
                    "operation_id": operation.id,
                    "due_date": purchase.due_date,
                    "total": purchase.total,
                },
            )
            self._repo.commit()
            return PurchaseView(purchase, self._repo.lines(purchase.id), None)
        except (SequenceNotConfiguredError, SequenceExhaustedError) as error:
            self._repo.rollback()
            return self.start_compensation(operation_id, inventory_operation_id, error, actor)
        except IntegrityError as error:
            self._repo.rollback()
            if violated_constraint(error) == UQ_NUMBER:
                logger.error("Número de compra repetido al confirmar operacion=%s", operation_id)
                return self.start_compensation(
                    operation_id, inventory_operation_id, SequenceInUseError(["number"]), actor
                )
            raise
        except Exception:
            self._repo.rollback()
            raise

    # ----------------------------------------------------------- compensación

    def start_compensation(
        self, operation_id: UUID, inventory_operation_id: UUID, cause: PurchaseError, actor: str
    ) -> PurchaseView:
        """Registra que la entrada aplicada debe revertirse (`COMPENSATION_PENDING`) y la revierte."""
        try:
            purchase, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(purchase, operation)
            now = self._clock()
            operation.error_code = COMPENSATION_PENDING
            operation.inventory_operation_id = inventory_operation_id
            operation.error_details = {"error": cause.to_record()}
            touch(operation, actor, now)
            self._repo.flush()
            self._repo.commit()
        except Exception:
            self._repo.rollback()
            raise
        logger.warning(
            "Compensación iniciada operacion=%s entrada=%s causa=%s", operation_id, inventory_operation_id, cause.code
        )
        return self.compensate(operation_id, actor)

    def compensate(self, operation_id: UUID, actor: str) -> PurchaseView:
        """Pide el reverso de la entrada aplicada; con éxito, cierra la operación `FAILED`."""
        purchase, operation = self.load(operation_id)
        if operation.status != PENDING or operation.error_code != COMPENSATION_PENDING:
            self._repo.end_read()
            return self.finished(purchase, operation)
        record = (operation.error_details or {}).get("error") or {}
        payload = {
            "operation_key": str(compensation_key(operation.id)),
            "company_id": str(purchase.company_id),
            # D-07: el usuario que inició la confirmación que produjo la entrada (inmutable en la operación).
            "application_user_id": str(operation.application_user_id),
            "correlation_id": str(operation.correlation_id),
            "reason": f"Compensación automática: la compra no pudo confirmarse ({record.get('code')}).",
        }
        entry_id = operation.inventory_operation_id
        self._repo.end_read()

        try:
            reversal = self._inventory.reverse_entry(entry_id, payload)
        except DependencyUnavailableError as error:
            logger.error("Compensación pendiente: Inventory no disponible operacion=%s", operation_id)
            error.context["operation_id"] = str(operation_id)
            raise
        except InventoryRejection as rejection:
            logger.critical(
                "Compensación rechazada por Inventory operacion=%s entrada=%s codigo=%s: queda PENDING para revisión",
                operation_id,
                entry_id,
                rejection.code,
            )
            raise InventoryRejectedError(rejection.code, rejection.status) from None

        try:
            purchase, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(purchase, operation)
            now = self._clock()
            operation.status = FAILED
            operation.error_code = str(record.get("code") or COMPENSATION_PENDING)
            operation.error_details = {"error": record, "compensation_operation_id": str(reversal.id)}
            operation.completed_at = now
            touch(operation, actor, now)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.CONFIRM_PURCHASE,
                entity_type=audit.PURCHASE,
                entity_id=purchase.id,
                company_id=purchase.company_id,
                branch_id=purchase.branch_id,
                application_user_id=operation.application_user_id,
                correlation_id=operation.correlation_id,
                result="FAILURE",
                reason=f"Entrada revertida por compensación: {operation.error_code}",
                new_values={
                    "operation_id": operation.id,
                    "inventory_operation_id": entry_id,
                    "compensation_operation_id": reversal.id,
                    "error_code": operation.error_code,
                },
            )
            self._repo.commit()
        except Exception:
            self._repo.rollback()
            raise
        logger.warning("Compensación aplicada operacion=%s reverso=%s", operation_id, reversal.id)
        raise StoredError(record)

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
                action=audit.CONFIRM_PURCHASE if operation.operation_type == CONFIRM else audit.CANCEL_PURCHASE,
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
        """Pide a Inventory el reverso exacto de `inventory_operation_id` y aplica el resultado (R-09)."""
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
