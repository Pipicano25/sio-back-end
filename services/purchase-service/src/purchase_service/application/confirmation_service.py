"""Confirmación de compras (Historia 2; FR-015 a FR-025; research.md R-04, R-05).

1. Acceso a la sucursal, idempotencia (`Idempotency-Key` ligada a compra, tipo y `sub`).
2. Validación completa de referencias y del usuario operativo, y comprobación de la
   secuencia aplicable, **fuera de transacción**.
3. T1: bloqueo de la compra; revalida estado, versión, líneas y operación en curso;
   refresca y congela snapshots y `due_date`; registra la operación `CONFIRM` `PENDING`.
4. Llamada a Inventory con la clave = `id` de la operación (la misma en todo reintento).
5. T2 (`OperationEngine.complete_confirmation`): número del período, `CONFIRMED` y
   `SUCCEEDED` en una transacción; o `FAILED`; o `PENDING` si Inventory no responde.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from purchase_service.application.branch_access import require_branch_access
from purchase_service.application.exceptions import (
    IdempotencyKeyConflictError,
    InvalidStatusError,
    NotFoundError,
    OperationInProgressError,
    PurchaseWithoutLinesError,
    SequenceExhaustedError,
    SequenceNotConfiguredError,
    VersionConflictError,
)
from purchase_service.application.operation_engine import OperationEngine
from purchase_service.application.purchase_service import Actor, PurchaseView
from purchase_service.application.reference_validation import HeaderInput, LineInput, ReferenceResolver, resolve_together
from purchase_service.application.snapshots import apply_header, apply_line, touch
from purchase_service.domain.numbering import exceeds_maximum, next_value, period_key
from purchase_service.domain.status import CONFIRM, DRAFT, PENDING
from purchase_service.infrastructure.models import Purchase, PurchaseOperation
from purchase_service.infrastructure.repository import UQ_IDEMPOTENCY_KEY, UQ_PENDING, PurchaseRepository, violated_constraint
from purchase_service.infrastructure.sequence_repository import SequenceRepository


def check_key_owner(operation: PurchaseOperation, company_id: UUID, purchase_id: UUID, operation_type: str, subject: str) -> None:
    """La clave pertenece a otra compra, otro tipo u otra identidad → `409` sin revelar el original (R-04)."""
    if (
        operation.company_id != company_id
        or operation.purchase_id != purchase_id
        or operation.operation_type != operation_type
        or operation.created_by != subject
    ):
        raise IdempotencyKeyConflictError()


class ConfirmationService:
    def __init__(
        self,
        repository: PurchaseRepository,
        sequences: SequenceRepository,
        resolver: ReferenceResolver,
        engine: OperationEngine,
        *,
        clock: Callable[[], datetime],
    ) -> None:
        self._repo = repository
        self._sequences = sequences
        self._resolver = resolver
        self._engine = engine
        self._clock = clock

    def _replay(self, operation: PurchaseOperation, company_id: UUID, purchase_id: UUID, actor: Actor) -> PurchaseView:
        check_key_owner(operation, company_id, purchase_id, operation.operation_type, actor.subject)
        if operation.status == PENDING:
            if operation.operation_type == CONFIRM:
                return self._engine.run_confirmation(operation.id, actor.subject)
            return self._engine.run_cancellation(operation.id, actor.subject)
        purchase = self._repo.get_purchase(company_id, purchase_id)
        if purchase is None:
            raise NotFoundError()
        return self._engine.finished(purchase, operation)

    def existing_key(
        self, key: str, company_id: UUID, purchase_id: UUID, operation_type: str, actor: Actor
    ) -> PurchaseView | None:
        operation = self._repo.operation_by_key(key)
        if operation is None:
            return None
        check_key_owner(operation, company_id, purchase_id, operation_type, actor.subject)
        self._repo.end_read()
        return self._replay(operation, company_id, purchase_id, actor)

    def _check_sequence(self, purchase: Purchase) -> None:
        sequence = self._sequences.applicable(purchase.company_id, purchase.branch_id)
        if sequence is None:
            raise SequenceNotConfiguredError()
        period = period_key(sequence.reset_policy, purchase.operation_date)
        upcoming = next_value(self._sequences.current(sequence.id, period), sequence.initial_number)
        if exceeds_maximum(upcoming, sequence.maximum_number, sequence.number_length):
            raise SequenceExhaustedError(period)

    def confirm(
        self,
        company_id: UUID,
        purchase_id: UUID,
        version: int,
        idempotency_key: str,
        correlation_id: UUID | None,
        actor: Actor,
    ) -> PurchaseView:
        purchase = self._repo.get_purchase(company_id, purchase_id)
        if purchase is None:
            raise NotFoundError()
        self._repo.end_read()
        operator = require_branch_access(actor.access, company_id, purchase.branch_id)

        replayed = self.existing_key(idempotency_key, company_id, purchase_id, CONFIRM, actor)
        if replayed is not None:
            return replayed

        pending = self._repo.pending_operation(purchase.id)
        if pending is not None:
            raise OperationInProgressError(pending.id)
        if purchase.status != DRAFT:
            raise InvalidStatusError(purchase.status)
        if purchase.version != version:
            raise VersionConflictError()
        lines = self._repo.lines(purchase.id)
        if not lines:
            raise PurchaseWithoutLinesError()
        self._repo.end_read()

        company = replace(self._resolver.company(company_id), default_currency=purchase.currency_code)
        header_snapshot, line_snapshots = resolve_together(
            lambda: self._resolver.resolve_header(
                company,
                HeaderInput(
                    branch_id=purchase.branch_id,
                    company_supplier_id=purchase.company_supplier_id,
                    operation_date=purchase.operation_date,
                    supplier_payment_condition_id=purchase.supplier_payment_condition_id,
                ),
            ),
            lambda: self._resolver.resolve_lines(
                company_id,
                purchase.company_supplier_id,
                [
                    LineInput(
                        line.company_product_id,
                        line.company_product_presentation_id,
                        line.supplier_product_id,
                        line.quantity,
                        field_prefix=f"lines[{index}].",
                        line_number=line.line_number,
                    )
                    for index, line in enumerate(lines)
                ],
            ),
        )
        self._resolver.check_operator(company_id, operator.application_user_id)
        self._check_sequence(purchase)
        self._repo.end_read()

        now = self._clock()
        try:
            self._repo.begin()
            locked = self._repo.lock_purchase(company_id, purchase_id)
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
            for line, snapshot in zip(current_lines, line_snapshots, strict=True):
                apply_line(line, snapshot)
                touch(line, actor.subject, now)
            touch(locked, actor.subject, now)
            operation = PurchaseOperation(
                id=uuid4(),
                company_id=company_id,
                purchase_id=locked.id,
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
                replayed = self.existing_key(idempotency_key, company_id, purchase_id, CONFIRM, actor)
                if replayed is not None:
                    return replayed
            if constraint == UQ_PENDING:
                pending = self._repo.pending_operation(purchase_id)
                raise OperationInProgressError(pending.id if pending else "") from None
            raise
        except Exception:
            self._repo.rollback()
            raise

        return self._engine.run_confirmation(operation.id, actor.subject)
