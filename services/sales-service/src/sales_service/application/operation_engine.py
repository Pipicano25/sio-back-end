"""Finalización de operaciones distribuidas (research.md R-04, R-05, R-09 a R-11, R-16; RC-01, RC-03, RC-06).

Venta e Inventory están en bases distintas: no hay una transacción común. Cada
operación (`sale_operations`) se registra `PENDING` **antes** de llamar a Inventory y su
`id` es la clave de operación enviada; el resultado se aplica después en una transacción
local corta. Lo usan la solicitud original, sus reintentos con la misma clave de
idempotencia y el conciliador; el bloqueo de la operación garantiza que a lo sumo uno la
completa.

Orden de bloqueo: venta → operación → contador de secuencia.

Confirmación (T2): con la salida aplicada, se copian a cada línea el costo FIFO que
informa Inventory (por unidad base, sin convertir ni recalcular; P-05) y `cost_known`, se
calcula el margen (P-01, C-03), se asigna el número del período de `operation_date` (fijada
en T1) y la venta pasa a `CONFIRMED`; todo en una transacción. Las líneas se escriben
**antes** de cambiar el estado de la venta (el trigger solo admite cambios de líneas en
`DRAFT`).

Compensación (R-05 paso 7): si Inventory aplicó la salida pero la venta no puede quedar
`CONFIRMED` por una causa definitiva de numeración, se registra `COMPENSATION_PENDING` y se
pide el reverso de la salida con una clave derivada y como usuario operativo el que inició
la confirmación (`application_user_id` de la operación, inmutable). Si el reverso no puede
aplicarse, la operación **sigue `PENDING`**, visible y reconciliable. Nunca se consume un
número sin confirmar la venta.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.exc import IntegrityError

from sales_service.application import audit_events as audit
from sales_service.application.exceptions import (
    INVENTORY,
    DependencyUnavailableError,
    InsufficientStockError,
    InventoryRejectedError,
    NotFoundError,
    SalesError,
    SequenceExhaustedError,
    SequenceInUseError,
    SequenceNotConfiguredError,
    StoredError,
)
from sales_service.application.ports import InventoryGateway, InventoryOperationRef, InventoryRejection
from sales_service.application.sale_service import SaleView
from sales_service.application.snapshots import apply_cost, line_base_quantity, touch
from sales_service.domain.numbering import exceeds_maximum, format_number, period_key
from sales_service.domain.status import (
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
from sales_service.infrastructure.models import Sale, SaleDetail, SaleOperation
from sales_service.infrastructure.repository import SaleRepository, violated_constraint
from sales_service.infrastructure.sequence_repository import SequenceRepository
from sales_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

UQ_NUMBER = "uq_sales_company_number"
ORIGIN_TYPE = "SALE"
COMPENSATION_NAMESPACE = uuid5(NAMESPACE_URL, "sio:sales-service:compensation")
INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
MARGIN_LOG_EVENT = "sales.margin.percentage_outcome"


def compensation_key(operation_id: UUID) -> UUID:
    """Clave estable del reverso compensatorio de una confirmación (misma en todo reintento)."""
    return uuid5(COMPENSATION_NAMESPACE, str(operation_id))


def stored_error(operation: SaleOperation) -> StoredError:
    details = operation.error_details or {}
    record = details.get("error") or {"code": operation.error_code, "message": "La operación falló."}
    return StoredError(record)


def shortages_by_line(rejection: InventoryRejection, lines: list[SaleDetail]) -> list[dict]:
    """`shortages[i].index` de Inventory → líneas de la venta (FR-020)."""
    shortages = rejection.body.get("shortages") if isinstance(rejection.body, dict) else None
    result: list[dict] = []
    for item in shortages if isinstance(shortages, list) else []:
        index = item.get("index") if isinstance(item, dict) else None
        line = lines[index] if isinstance(index, int) and 0 <= index < len(lines) else None
        result.append(
            {
                "line_numbers": [line.line_number] if line is not None else [],
                "company_product_id": item.get("company_product_id") if isinstance(item, dict) else None,
                "available": item.get("available") if isinstance(item, dict) else None,
                "requested": item.get("requested") if isinstance(item, dict) else None,
            }
        )
    return result


def map_rejection(rejection: InventoryRejection, operation_type: str, lines: list[SaleDetail]) -> SalesError:
    if operation_type == CONFIRM and rejection.status == 409 and rejection.code == INSUFFICIENT_STOCK:
        return InsufficientStockError(shortages_by_line(rejection, lines))
    logger.error(
        "Inventory rechazó la operación tipo=%s estado=%s codigo=%s", operation_type, rejection.status, rejection.code
    )
    return InventoryRejectedError(rejection.code, rejection.status)


class OperationEngine:
    def __init__(
        self,
        repository: SaleRepository,
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

    def _view(self, sale: Sale) -> SaleView:
        pending = self._repo.pending_operation(sale.id)
        return SaleView(sale, self._repo.lines(sale.id), pending.id if pending else None)

    def _lock(self, operation_id: UUID) -> tuple[Sale, SaleOperation]:
        """Bloquea venta y operación en el orden fijo (venta → operación)."""
        self._repo.begin()
        snapshot = self._repo.session.get(SaleOperation, operation_id, populate_existing=True)
        if snapshot is None:
            raise NotFoundError()
        sale = self._repo.lock_sale(snapshot.company_id, snapshot.sale_id)
        operation = self._repo.lock_operation(operation_id)
        if sale is None or operation is None:
            raise NotFoundError()
        return sale, operation

    def finished(self, sale: Sale, operation: SaleOperation) -> SaleView:
        """Resultado de una operación ya terminada: la venta actual o el error original."""
        if operation.status == SUCCEEDED:
            return self._view(sale)
        raise stored_error(operation)

    def load(self, operation_id: UUID) -> tuple[Sale, SaleOperation]:
        operation = self._repo.session.get(SaleOperation, operation_id, populate_existing=True)
        if operation is None:
            raise NotFoundError()
        sale = self._repo.get_sale(operation.company_id, operation.sale_id)
        if sale is None:
            raise NotFoundError()
        return sale, operation

    def claim(self, operation_id: UUID, actor: str) -> tuple[Sale, SaleOperation] | SaleView:
        """Toma la operación para continuarla: marca `updated_at` (anula una marca del conciliador)."""
        try:
            sale, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(sale, operation)
            touch(operation, actor, self._clock())
            self._repo.flush()
            self._repo.commit()
            return sale, operation
        except Exception:
            self._repo.rollback()
            raise

    # ------------------------------------------------------------- Inventory

    def output_payload(self, sale: Sale, operation: SaleOperation, lines: list[SaleDetail]) -> dict:
        """Solicitud de salida, determinista a partir de lo congelado (la misma en todo reintento).

        Sin `unit_cost`: Inventory calcula el costo FIFO de la salida (contrato 012 + 013).
        """
        return {
            "operation_key": str(operation.id),
            "company_id": str(sale.company_id),
            "branch_id": str(sale.branch_id),
            "origin_type": ORIGIN_TYPE,
            "origin_id": str(sale.id),
            "application_user_id": str(operation.application_user_id),
            "correlation_id": str(operation.correlation_id),
            "reason": None,
            "lines": [
                {
                    "origin_detail_id": str(line.id),
                    "company_product_id": str(line.company_product_id),
                    "quantity": format(line_base_quantity(line), "f"),
                }
                for line in lines
            ],
        }

    def run_confirmation(self, operation_id: UUID, actor: str) -> SaleView:
        """Llama a Inventory con la clave de la operación y aplica el resultado (R-05 pasos 5–7)."""
        claimed = self.claim(operation_id, actor)
        if isinstance(claimed, SaleView):
            return claimed
        sale, operation = claimed

        if operation.error_code == COMPENSATION_PENDING:
            return self.compensate(operation_id, actor)

        lines = self._repo.lines(sale.id)
        payload = self.output_payload(sale, operation, lines)
        self._repo.end_read()

        try:
            reference = self._inventory.apply_output(payload)
        except InventoryRejection as rejection:
            error = map_rejection(rejection, CONFIRM, lines)
            self.fail(operation_id, error, actor)
            raise error from None
        except DependencyUnavailableError as error:
            error.context["operation_id"] = str(operation_id)
            raise

        return self.complete_confirmation(operation_id, reference, actor)

    def _apply_costs(self, sale: Sale, lines: list[SaleDetail], output: InventoryOperationRef) -> bool:
        """Costo y margen por línea con los movimientos de la salida; devuelve `has_unknown_cost`."""
        by_detail = {movement.origin_detail_id: movement for movement in output.movements}
        missing = [line.line_number for line in lines if line.id not in by_detail]
        if missing:
            logger.error(
                "Salida de Inventory sin movimiento para las líneas venta=%s salida=%s lineas=%s",
                sale.id,
                output.id,
                missing,
            )
            raise DependencyUnavailableError(INVENTORY, operation="inventory_output", cause="salida_sin_movimientos")
        unknown = False
        outcomes = []
        for line in lines:
            margin = apply_cost(line, by_detail[line.id])
            unknown = unknown or not line.cost_known
            outcomes.append(f"{line.line_number}:{margin.outcome}")
        # Una línea de log por venta con el motivo del porcentaje de cada línea (P-01).
        logger.info("%s venta=%s resultados=%s", MARGIN_LOG_EVENT, sale.id, ",".join(outcomes))
        return unknown

    def complete_confirmation(self, operation_id: UUID, output: InventoryOperationRef, actor: str) -> SaleView:
        """Transacción T2: costo y margen, número del período, `CONFIRMED`, `SUCCEEDED` y auditoría, todo o nada."""
        try:
            sale, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(sale, operation)
            if operation.error_code == COMPENSATION_PENDING:
                self._repo.commit()
                return self.compensate(operation_id, actor)
            if sale.status != DRAFT:
                raise RuntimeError(f"Venta {sale.id} en {sale.status} con confirmación pendiente")

            sequence = self._sequences.applicable(sale.company_id, sale.branch_id)
            if sequence is None:
                raise SequenceNotConfiguredError()
            period = period_key(sequence.reset_policy, sale.operation_date)
            value = self._sequences.assign(sequence, period, actor)
            if exceeds_maximum(value, sequence.maximum_number, sequence.number_length):
                raise SequenceExhaustedError(period)

            now = self._clock()
            lines = self._repo.lines(sale.id)
            has_unknown_cost = self._apply_costs(sale, lines, output)
            for line in lines:
                touch(line, actor, now)
            # Las líneas se escriben mientras la venta sigue en DRAFT (trigger de líneas).
            self._repo.flush()

            sale.number = format_number(sequence.prefix, sequence.separator, period, value, sequence.number_length)
            sale.sequence_value = value
            sale.sale_sequence_id = sequence.id
            sale.inventory_operation_id = output.id
            sale.has_unknown_cost = has_unknown_cost
            sale.status = CONFIRMED
            touch(sale, actor, now)
            operation.status = SUCCEEDED
            operation.inventory_operation_id = output.id
            operation.completed_at = now
            operation.error_code = None
            operation.error_details = None
            touch(operation, actor, now)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.CONFIRM_SALE,
                entity_type=audit.SALE,
                entity_id=sale.id,
                company_id=sale.company_id,
                branch_id=sale.branch_id,
                application_user_id=operation.application_user_id,
                correlation_id=operation.correlation_id,
                previous_values={"status": DRAFT},
                new_values={
                    "status": CONFIRMED,
                    "number": sale.number,
                    "sequence_value": value,
                    "sale_sequence_id": sequence.id,
                    "inventory_operation_id": output.id,
                    "operation_id": operation.id,
                    "operation_date": sale.operation_date,
                    "due_date": sale.due_date,
                    "total": sale.total,
                },
            )
            self._repo.commit()
            return SaleView(sale, lines, None)
        except (SequenceNotConfiguredError, SequenceExhaustedError) as error:
            self._repo.rollback()
            return self.start_compensation(operation_id, output.id, error, actor)
        except IntegrityError as error:
            self._repo.rollback()
            if violated_constraint(error) == UQ_NUMBER:
                logger.error("Número de venta repetido al confirmar operacion=%s", operation_id)
                return self.start_compensation(operation_id, output.id, SequenceInUseError(["number"]), actor)
            raise
        except Exception:
            self._repo.rollback()
            raise

    # ----------------------------------------------------------- compensación

    def start_compensation(
        self, operation_id: UUID, inventory_operation_id: UUID, cause: SalesError, actor: str
    ) -> SaleView:
        """Registra que la salida aplicada debe revertirse (`COMPENSATION_PENDING`) y la revierte."""
        try:
            sale, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(sale, operation)
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
            "Compensación iniciada operacion=%s salida=%s causa=%s", operation_id, inventory_operation_id, cause.code
        )
        return self.compensate(operation_id, actor)

    def compensate(self, operation_id: UUID, actor: str) -> SaleView:
        """Pide el reverso de la salida aplicada; con éxito, cierra la operación `FAILED`."""
        sale, operation = self.load(operation_id)
        if operation.status != PENDING or operation.error_code != COMPENSATION_PENDING:
            self._repo.end_read()
            return self.finished(sale, operation)
        record = (operation.error_details or {}).get("error") or {}
        payload = {
            "operation_key": str(compensation_key(operation.id)),
            "company_id": str(sale.company_id),
            # El usuario que inició la confirmación que produjo la salida (inmutable en la operación).
            "application_user_id": str(operation.application_user_id),
            "correlation_id": str(operation.correlation_id),
            "reason": f"Compensación automática: la venta no pudo confirmarse ({record.get('code')}).",
        }
        output_id = operation.inventory_operation_id
        self._repo.end_read()

        try:
            reversal = self._inventory.reverse_output(output_id, payload)
        except DependencyUnavailableError as error:
            logger.error("Compensación pendiente: Inventory no disponible operacion=%s", operation_id)
            error.context["operation_id"] = str(operation_id)
            raise
        except InventoryRejection as rejection:
            logger.critical(
                "Compensación rechazada por Inventory operacion=%s salida=%s codigo=%s: queda PENDING para revisión",
                operation_id,
                output_id,
                rejection.code,
            )
            raise InventoryRejectedError(rejection.code, rejection.status) from None

        try:
            sale, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(sale, operation)
            now = self._clock()
            operation.status = FAILED
            operation.error_code = str(record.get("code") or COMPENSATION_PENDING)
            operation.error_details = {"error": record, "compensation_operation_id": str(reversal.id)}
            operation.completed_at = now
            touch(operation, actor, now)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.CONFIRM_SALE,
                entity_type=audit.SALE,
                entity_id=sale.id,
                company_id=sale.company_id,
                branch_id=sale.branch_id,
                application_user_id=operation.application_user_id,
                correlation_id=operation.correlation_id,
                result="FAILURE",
                reason=f"Salida revertida por compensación: {operation.error_code}",
                new_values={
                    "operation_id": operation.id,
                    "inventory_operation_id": output_id,
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
        error: SalesError,
        actor: str,
        *,
        marker: datetime | None = None,
    ) -> bool:
        """Cierra la operación `FAILED` con el error; con `marker`, solo si nadie la tocó desde la marca."""
        try:
            sale, operation = self._lock(operation_id)
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
                action=audit.CONFIRM_SALE if operation.operation_type == CONFIRM else audit.CANCEL_SALE,
                entity_type=audit.SALE,
                entity_id=sale.id,
                company_id=sale.company_id,
                branch_id=sale.branch_id,
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

    def run_cancellation(self, operation_id: UUID, actor: str) -> SaleView:
        """Pide a Inventory el reverso exacto de `inventory_operation_id` y aplica el resultado (R-11)."""
        claimed = self.claim(operation_id, actor)
        if isinstance(claimed, SaleView):
            return claimed
        sale, operation = claimed
        payload = {
            "operation_key": str(operation.id),
            "company_id": str(sale.company_id),
            "application_user_id": str(operation.application_user_id),
            "correlation_id": str(operation.correlation_id),
            "reason": operation.reason,
        }
        output_id = sale.inventory_operation_id
        self._repo.end_read()

        try:
            reversal = self._inventory.reverse_output(output_id, payload)
        except InventoryRejection as rejection:
            error = map_rejection(rejection, CANCEL, [])
            self.fail(operation_id, error, actor)
            raise error from None
        except DependencyUnavailableError as error:
            error.context["operation_id"] = str(operation_id)
            raise

        return self.complete_cancellation(operation_id, reversal.id, actor)

    def complete_cancellation(self, operation_id: UUID, reversal_id: UUID, actor: str) -> SaleView:
        try:
            sale, operation = self._lock(operation_id)
            if operation.status != PENDING:
                self._repo.commit()
                return self.finished(sale, operation)
            if sale.status != CONFIRMED:
                raise RuntimeError(f"Venta {sale.id} en {sale.status} con anulación pendiente")
            now = self._clock()
            sale.status = CANCELLED
            sale.cancelled_by_user_id = operation.application_user_id
            sale.cancelled_at = now
            sale.cancellation_reason = operation.reason
            touch(sale, actor, now)
            operation.status = SUCCEEDED
            operation.inventory_operation_id = reversal_id
            operation.completed_at = now
            touch(operation, actor, now)
            self._repo.flush()
            audit.record(
                self._repo.session,
                action=audit.CANCEL_SALE,
                entity_type=audit.SALE,
                entity_id=sale.id,
                company_id=sale.company_id,
                branch_id=sale.branch_id,
                application_user_id=sale.cancelled_by_user_id,
                correlation_id=operation.correlation_id,
                reason=sale.cancellation_reason,
                previous_values={"status": CONFIRMED},
                new_values={
                    "status": CANCELLED,
                    "number": sale.number,
                    "inventory_operation_id": sale.inventory_operation_id,
                    "reversal_operation_id": reversal_id,
                    "operation_id": operation.id,
                },
            )
            self._repo.commit()
            return SaleView(sale, self._repo.lines(sale.id), None)
        except Exception:
            self._repo.rollback()
            raise
