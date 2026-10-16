"""Confirmación de ventas (Historia 2; FR-014 a FR-023; research.md R-04, R-05, R-07, R-08, R-12).

1. Acceso a la sucursal, idempotencia (`Idempotency-Key` ligada a venta, tipo y `sub`),
   operación en curso antes que versión (D-10 (014)).
2. Fuera de transacción: revalidación de cliente, productos, presentaciones y usuario
   operativo, y **nueva resolución del precio** con la intención original de cada línea
   (P-02); si el precio, la lista o el ítem cambiaron → `409 PRICES_CHANGED` sin efectos (DS-05).
3. Consulta previa de existencias (informativa; la barrera real es Inventory, RC-04; si Inventory
   no responde se omite y la salida deja la operación `PENDING`) y
   secuencia aplicable al período de la fecha del día en la zona de la sucursal.
4. T1: bloqueo de la venta; revalida estado, versión, líneas y operación en curso; fija
   `operation_date` y `due_date` (R-12), congela snapshots; registra la operación `CONFIRM`
   `PENDING`. Un reintento o el conciliador conservan esa fecha.
5. Llamada a Inventory con la clave = `id` de la operación (la misma en todo reintento).
6. T2 (`OperationEngine.complete_confirmation`).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import date, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from sales_service.application.availability import shortages, summarize
from sales_service.application.branch_access import require_branch_access
from sales_service.application.exceptions import (
    DependencyUnavailableError,
    IdempotencyKeyConflictError,
    InsufficientStockError,
    InvalidStatusError,
    NotFoundError,
    OperationInProgressError,
    PricesChangedError,
    SaleWithoutLinesError,
    SequenceExhaustedError,
    SequenceNotConfiguredError,
    ValidationFailedError,
    VersionConflictError,
    field_error,
)
from sales_service.application.operation_engine import OperationEngine
from sales_service.application.ports import CompanyInfo, InventoryGateway
from sales_service.application.reference_validation import (
    HeaderInput,
    LineInput,
    LineSnapshot,
    ReferenceResolver,
    resolve_together,
    today_in,
)
from sales_service.application.sale_service import Actor, SaleView
from sales_service.application.snapshots import apply_business_date, apply_header, apply_line, touch
from sales_service.domain.money import QUANTITY_QUANTUM, TAX_NOT_ALLOWED_MESSAGE
from sales_service.domain.numbering import exceeds_maximum, next_value, period_key
from sales_service.domain.pricing import PriceRef, list_to_request, price_changed
from sales_service.domain.status import CONFIRM, DRAFT, PENDING
from sales_service.infrastructure.models import Sale, SaleDetail, SaleOperation
from sales_service.infrastructure.repository import UQ_IDEMPOTENCY_KEY, UQ_PENDING, SaleRepository, violated_constraint
from sales_service.infrastructure.sequence_repository import SequenceRepository
from sales_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)


def check_key_owner(operation: SaleOperation, company_id: UUID, sale_id: UUID, operation_type: str, subject: str) -> None:
    """La clave pertenece a otra venta, otro tipo u otra identidad → `409` sin revelar el original (R-04)."""
    if (
        operation.company_id != company_id
        or operation.sale_id != sale_id
        or operation.operation_type != operation_type
        or operation.created_by != subject
    ):
        raise IdempotencyKeyConflictError()


def _price_text(value) -> str | None:
    return None if value is None else str(value)


def price_differences(lines: list[SaleDetail], snapshots: list[LineSnapshot]) -> list[dict]:
    """Líneas cuyo precio vigente difiere del guardado (DS-05), con ambos valores."""
    changes = []
    for index, (line, snapshot) in enumerate(zip(lines, snapshots, strict=True)):
        stored = PriceRef(line.unit_price, line.price_list_id, line.price_list_item_id)
        current = PriceRef(snapshot.unit_price, snapshot.price_list_id, snapshot.price_list_item_id)
        if price_changed(stored, current):
            changes.append(
                {
                    "field": f"lines[{index}].unit_price",
                    "line_number": line.line_number,
                    "code": "PRICE_CHANGED",
                    "message": "El precio aplicable de la línea cambió desde que se guardó.",
                    "stored": {
                        "unit_price": format(stored.unit_price.quantize(QUANTITY_QUANTUM), "f"),
                        "price_list_id": _price_text(stored.price_list_id),
                        "price_list_item_id": _price_text(stored.price_list_item_id),
                    },
                    "current": {
                        "unit_price": format(current.unit_price.quantize(QUANTITY_QUANTUM), "f"),
                        "price_list_id": _price_text(current.price_list_id),
                        "price_list_item_id": _price_text(current.price_list_item_id),
                    },
                }
            )
    return changes


class ConfirmationService:
    def __init__(
        self,
        repository: SaleRepository,
        sequences: SequenceRepository,
        resolver: ReferenceResolver,
        engine: OperationEngine,
        inventory: InventoryGateway,
        *,
        clock: Callable[[], datetime],
    ) -> None:
        self._repo = repository
        self._sequences = sequences
        self._resolver = resolver
        self._engine = engine
        self._inventory = inventory
        self._clock = clock

    def _replay(self, operation: SaleOperation, company_id: UUID, sale_id: UUID, actor: Actor) -> SaleView:
        check_key_owner(operation, company_id, sale_id, operation.operation_type, actor.subject)
        if operation.status == PENDING:
            if operation.operation_type == CONFIRM:
                return self._engine.run_confirmation(operation.id, actor.subject)
            return self._engine.run_cancellation(operation.id, actor.subject)
        sale = self._repo.get_sale(company_id, sale_id)
        if sale is None:
            raise NotFoundError()
        return self._engine.finished(sale, operation)

    def existing_key(
        self, key: str, company_id: UUID, sale_id: UUID, operation_type: str, actor: Actor
    ) -> SaleView | None:
        operation = self._repo.operation_by_key(key)
        if operation is None:
            return None
        check_key_owner(operation, company_id, sale_id, operation_type, actor.subject)
        self._repo.end_read()
        return self._replay(operation, company_id, sale_id, actor)

    def _balances(self, company_id: UUID, branch_id: UUID, lines: list[SaleDetail]):
        """Saldos para la consulta previa; `None` si Inventory no responde (la consulta es informativa)."""
        try:
            product_ids = list(dict.fromkeys(line.company_product_id for line in lines))
            return self._inventory.lookup_balances(company_id, branch_id, product_ids)
        except DependencyUnavailableError:
            # Sin consulta previa se sigue: la barrera es la salida en Inventory, que con Inventory
            # caído deja la operación PENDING y reconciliable (R-08; Historia 2, escenario 4).
            logger.warning("Consulta previa de existencias omitida: Inventory no disponible")
            return None

    def _check_sequence(self, sale: Sale, business_date: date) -> None:
        sequence = self._sequences.applicable(sale.company_id, sale.branch_id)
        if sequence is None:
            raise SequenceNotConfiguredError()
        period = period_key(sequence.reset_policy, business_date)
        upcoming = next_value(self._sequences.current(sequence.id, period), sequence.initial_number)
        if exceeds_maximum(upcoming, sequence.maximum_number, sequence.number_length):
            raise SequenceExhaustedError(period)

    def confirm(
        self,
        company_id: UUID,
        sale_id: UUID,
        version: int,
        idempotency_key: str,
        correlation_id: UUID | None,
        actor: Actor,
    ) -> SaleView:
        sale = self._repo.get_sale(company_id, sale_id)
        if sale is None:
            raise NotFoundError()
        self._repo.end_read()
        operator = require_branch_access(actor.access, company_id, sale.branch_id)

        replayed = self.existing_key(idempotency_key, company_id, sale_id, CONFIRM, actor)
        if replayed is not None:
            return replayed

        pending = self._repo.pending_operation(sale.id)
        if pending is not None:
            raise OperationInProgressError(pending.id)
        if sale.status != DRAFT:
            raise InvalidStatusError(sale.status)
        if sale.version != version:
            raise VersionConflictError()
        lines = self._repo.lines(sale.id)
        if not lines:
            raise SaleWithoutLinesError()
        self._repo.end_read()
        # Spec 020 (FR-020-13, RC-MVP-6): un borrador anterior con descuento no se confirma.
        discounted = [
            field_error(
                f"lines[{index}].discount_amount",
                "DISCOUNT_NOT_ALLOWED",
                "Las ventas del MVP no admiten descuentos: el precio es el de la lista de precios.",
                line_number=line.line_number,
            )
            for index, line in enumerate(lines)
            if line.discount_amount != 0
        ] + [
            # Spec 021 (B-4, FR-021-30): un borrador anterior con impuesto tampoco se confirma.
            field_error(
                f"lines[{index}].tax_amount",
                "TAX_NOT_ALLOWED",
                TAX_NOT_ALLOWED_MESSAGE,
                line_number=line.line_number,
            )
            for index, line in enumerate(lines)
            if line.tax_amount != 0
        ]
        if discounted:
            raise ValidationFailedError(discounted)

        company = self._resolver.company(company_id)
        company = CompanyInfo(company.id, company.status, sale.currency_code)
        # Consultas independientes en paralelo (sin sesión de base): referencias y precio, usuario
        # operativo y saldos. El orden de los rechazos no cambia: referencias (422/409), precio
        # cambiado, usuario operativo, existencias.
        with ThreadPoolExecutor(max_workers=3) as pool:
            resolved = pool.submit(
                copy_context().run,
                resolve_together,
                lambda: self._resolver.resolve_header(
                    company, HeaderInput(sale.branch_id, sale.company_customer_id, sale.payment_method_id)
                ),
                lambda: self._resolver.resolve_lines(
                    company_id,
                    sale.currency_code,
                    [
                        LineInput(
                            line.company_product_id,
                            line.company_product_presentation_id,
                            list_to_request(price_list_requested=line.price_list_requested, price_list_id=line.price_list_id),
                            line.quantity,
                            field_prefix=f"lines[{index}].",
                            line_number=line.line_number,
                        )
                        for index, line in enumerate(lines)
                    ],
                ),
            )
            operator_check = pool.submit(
                copy_context().run, self._resolver.check_operator, company_id, operator.application_user_id
            )
            balances = pool.submit(copy_context().run, self._balances, company_id, sale.branch_id, lines)
            header_snapshot, line_snapshots = resolved.result()
            changes = price_differences(lines, line_snapshots)
            if changes:
                raise PricesChangedError(changes)
            operator_check.result()
            current_balances = balances.result()

        business_date = today_in(header_snapshot.branch_timezone, self._clock())
        if current_balances is not None:
            # Requerido con el factor ya revalidado (R-08).
            frozen = [
                SimpleNamespace(
                    company_product_id=line.company_product_id,
                    line_number=line.line_number,
                    quantity=line.quantity,
                    base_quantity_factor_snapshot=snapshot.factor,
                )
                for line, snapshot in zip(lines, line_snapshots, strict=True)
            ]
            missing = shortages(summarize(frozen, current_balances))
            if missing:
                raise InsufficientStockError(missing)
        self._check_sequence(sale, business_date)
        self._repo.end_read()

        now = self._clock()
        try:
            self._repo.begin()
            locked = self._repo.lock_sale(company_id, sale_id)
            if locked is None:
                raise NotFoundError()
            pending = self._repo.pending_operation(locked.id)
            if pending is not None:
                raise OperationInProgressError(pending.id)
            if locked.status != DRAFT:
                raise InvalidStatusError(locked.status)
            if locked.version != version:
                raise VersionConflictError()
            current_lines = self._repo.lines(locked.id)
            if [line.id for line in current_lines] != [line.id for line in lines]:
                raise VersionConflictError()

            apply_header(locked, header_snapshot)
            apply_business_date(locked, business_date)
            for line, snapshot in zip(current_lines, line_snapshots, strict=True):
                apply_line(line, snapshot)
                if self._repo.session.is_modified(line):  # solo las líneas cuyo snapshot cambió
                    touch(line, actor.subject, now)
            touch(locked, actor.subject, now)
            operation = SaleOperation(
                id=uuid4(),
                company_id=company_id,
                sale_id=locked.id,
                operation_type=CONFIRM,
                idempotency_key=idempotency_key,
                status=PENDING,
                correlation_id=correlation_id or uuid4(),
                application_user_id=operator.application_user_id,
                started_at=now,
                created_at=now,
                updated_at=now,
                created_by=actor.subject,
                updated_by=actor.subject,
            )
            self._repo.add(operation)
            self._repo.flush()
            self._repo.commit()
        except IntegrityError as error:
            self._repo.rollback()
            constraint = violated_constraint(error)
            if constraint == UQ_IDEMPOTENCY_KEY:
                replayed = self.existing_key(idempotency_key, company_id, sale_id, CONFIRM, actor)
                if replayed is not None:
                    return replayed
            if constraint == UQ_PENDING:
                pending = self._repo.pending_operation(sale_id)
                raise OperationInProgressError(pending.id if pending else "") from None
            raise
        except Exception:
            self._repo.rollback()
            raise

        return self._engine.run_confirmation(operation.id, actor.subject)
