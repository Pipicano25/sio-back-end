"""Recepción física completa de compras (spec 020; FR-020-02 a FR-020-05; RC-MVP-1, RC-MVP-2).

Confirmar una compra no mueve inventario: la mercancía ingresa a Inventory solo cuando el
usuario confirma explícitamente que recibió **toda** la compra (sin recepciones parciales,
por línea ni diferencias, DS-04). Reutiliza el motor de operaciones (DS-02):

1. Acceso a la sucursal e idempotencia (`Idempotency-Key` ligada a compra, tipo y `sub`).
2. Comprobaciones: compra `CONFIRMED`, no recibida, sin operación en curso, versión vigente;
   usuario operativo activo; costos congelados positivos (FR-020-04, FR-020-12). No vuelve a
   resolver proveedores ni productos: sus snapshots se congelaron al confirmar e Inventory
   valida los productos al aplicar la entrada.
3. T1: operación `RECEIVE` `PENDING`; su `id` es la clave de la entrada en Inventory.
4. `OperationEngine.run_receipt`: entrada en Inventory (unidad base, costo por unidad base) y T2
   (`received_at`, `received_by_user_id`, `inventory_operation_id`, `SUCCEEDED`). Si Inventory no
   responde, la operación queda `PENDING` (`503` con `operation_id`) para el reintento o el
   conciliador; nunca hay dos entradas.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from purchase_service.application.branch_access import require_branch_access
from purchase_service.application.confirmation_service import ConfirmationService
from purchase_service.application.exceptions import (
    InvalidStatusError,
    NotFoundError,
    OperationInProgressError,
    PurchaseAlreadyReceivedError,
    ValidationFailedError,
    VersionConflictError,
    field_error,
)
from purchase_service.application.operation_engine import OperationEngine
from purchase_service.application.purchase_service import Actor, PurchaseView
from purchase_service.application.reference_validation import ReferenceResolver
from purchase_service.application.snapshots import check_line_costs
from purchase_service.domain.money import DomainRuleError
from purchase_service.domain.status import CONFIRMED, PENDING, RECEIVE
from purchase_service.infrastructure.models import Purchase, PurchaseOperation
from purchase_service.infrastructure.repository import UQ_IDEMPOTENCY_KEY, UQ_PENDING, PurchaseRepository, violated_constraint


def require_receivable(purchase: Purchase, version: int) -> None:
    """Estado, recepción previa y versión, en ese orden."""
    if purchase.status != CONFIRMED:
        raise InvalidStatusError(purchase.status)
    if purchase.inventory_operation_id is not None:
        raise PurchaseAlreadyReceivedError()
    if purchase.version != version:
        raise VersionConflictError()


class ReceiptService:
    def __init__(
        self,
        repository: PurchaseRepository,
        confirmations: ConfirmationService,
        resolver: ReferenceResolver,
        engine: OperationEngine,
        *,
        clock: Callable[[], datetime],
    ) -> None:
        self._repo = repository
        self._keys = confirmations
        self._resolver = resolver
        self._engine = engine
        self._clock = clock

    def receive(
        self,
        company_id: UUID,
        purchase_id: UUID,
        version: int,
        full_receipt_confirmed: bool,
        idempotency_key: str,
        correlation_id: UUID | None,
        actor: Actor,
    ) -> PurchaseView:
        purchase = self._repo.get_purchase(company_id, purchase_id)
        if purchase is None:
            raise NotFoundError()
        self._repo.end_read()
        operator = require_branch_access(actor.access, company_id, purchase.branch_id)

        replayed = self._keys.existing_key(idempotency_key, company_id, purchase_id, RECEIVE, actor)
        if replayed is not None:
            return replayed

        if not full_receipt_confirmed:
            raise ValidationFailedError(
                [
                    field_error(
                        "full_receipt_confirmed",
                        "FULL_RECEIPT_NOT_CONFIRMED",
                        "Confirme que recibió toda la mercancía de la compra: no existen recepciones parciales.",
                    )
                ]
            )
        pending = self._repo.pending_operation(purchase.id)
        if pending is not None:
            raise OperationInProgressError(pending.id)
        require_receivable(purchase, version)
        errors = []
        for index, line in enumerate(self._repo.lines(purchase.id)):
            try:
                check_line_costs(line, prefix=f"lines[{index}].")
            except DomainRuleError as error:
                errors.append(field_error(error.field or f"lines[{index}].unit_cost", error.code, error.message))
        self._repo.end_read()
        if errors:
            raise ValidationFailedError(errors)
        self._resolver.check_operator(company_id, operator.application_user_id)

        now = self._clock()
        try:
            self._repo.begin()
            locked = self._repo.lock_purchase(company_id, purchase_id)
            if locked is None:
                raise NotFoundError()
            pending = self._repo.pending_operation(locked.id)
            if pending is not None:
                raise OperationInProgressError(pending.id)
            require_receivable(locked, version)
            operation = PurchaseOperation(
                id=uuid4(),
                company_id=company_id,
                purchase_id=locked.id,
                operation_type=RECEIVE,
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
                replayed = self._keys.existing_key(idempotency_key, company_id, purchase_id, RECEIVE, actor)
                if replayed is not None:
                    return replayed
            if constraint == UQ_PENDING:
                pending = self._repo.pending_operation(purchase_id)
                raise OperationInProgressError(pending.id if pending else "") from None
            raise
        except Exception:
            self._repo.rollback()
            raise

        return self._engine.run_receipt(operation.id, actor.subject)
