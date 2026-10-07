"""Anulación de compras (Historia 3; FR-026 a FR-030; research.md R-09).

- `DRAFT` → `CANCELLED` en una transacción local, sin Inventory; la operación `CANCEL`
  queda `SUCCEEDED` como traza y para la idempotencia.
- `CONFIRMED` → operación `CANCEL` `PENDING` (T1); reverso en Inventory de **exactamente**
  `inventory_operation_id` con la clave = `id` de la operación; T2 `CANCELLED` (conserva el
  número) y `SUCCEEDED` con el `id` del reverso, o `FAILED` y la compra sigue `CONFIRMED`.
- La anulación no revalida proveedor ni productos (pueden estar inactivos).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from purchase_service.application import audit_events as audit
from purchase_service.application.branch_access import require_branch_access
from purchase_service.application.confirmation_service import ConfirmationService
from purchase_service.application.exceptions import (
    InvalidStatusError,
    NotFoundError,
    OperationInProgressError,
    VersionConflictError,
)
from purchase_service.application.operation_engine import OperationEngine
from purchase_service.application.purchase_service import Actor, PurchaseView
from purchase_service.application.snapshots import touch
from purchase_service.domain.status import CANCEL, CANCELLED, CONFIRMED, DRAFT, PENDING, SUCCEEDED
from purchase_service.infrastructure.models import PurchaseOperation
from purchase_service.infrastructure.repository import UQ_IDEMPOTENCY_KEY, UQ_PENDING, PurchaseRepository, violated_constraint


class CancellationService:
    def __init__(
        self,
        repository: PurchaseRepository,
        confirmations: ConfirmationService,
        engine: OperationEngine,
        *,
        clock: Callable[[], datetime],
    ) -> None:
        self._repo = repository
        self._keys = confirmations
        self._engine = engine
        self._clock = clock

    def cancel(
        self,
        company_id: UUID,
        purchase_id: UUID,
        version: int,
        reason: str,
        idempotency_key: str,
        correlation_id: UUID | None,
        actor: Actor,
    ) -> PurchaseView:
        purchase = self._repo.get_purchase(company_id, purchase_id)
        if purchase is None:
            raise NotFoundError()
        self._repo.end_read()
        operator = require_branch_access(actor.access, company_id, purchase.branch_id)

        replayed = self._keys.existing_key(idempotency_key, company_id, purchase_id, CANCEL, actor)
        if replayed is not None:
            return replayed

        pending = self._repo.pending_operation(purchase.id)
        if pending is not None:
            raise OperationInProgressError(pending.id)
        if purchase.status == CANCELLED:
            raise InvalidStatusError(purchase.status)
        if purchase.version != version:
            raise VersionConflictError()
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
            if locked.status == CANCELLED:
                raise InvalidStatusError(locked.status)
            if locked.version != version:
                raise VersionConflictError()

            operation = PurchaseOperation(
                id=uuid4(),
                company_id=company_id,
                purchase_id=locked.id,
                operation_type=CANCEL,
                idempotency_key=idempotency_key,
                status=PENDING,
                correlation_id=correlation_id or uuid4(),
                application_user_id=operator.application_user_id,
                reason=reason,
                started_at=now,
                created_at=now,
                updated_at=now,
                created_by=actor.subject,
                updated_by=actor.subject,
            )

            if locked.status == DRAFT:
                # Borrador: anulación local, sin Inventory; la operación queda como traza (R-09).
                operation.status = SUCCEEDED
                operation.completed_at = now
                locked.status = CANCELLED
                locked.cancelled_by_user_id = operator.application_user_id
                locked.cancelled_at = now
                locked.cancellation_reason = reason
                touch(locked, actor.subject, now)
                self._repo.add(operation)
                self._repo.flush()
                audit.record(
                    self._repo.session,
                    action=audit.CANCEL_PURCHASE,
                    entity_type=audit.PURCHASE,
                    entity_id=locked.id,
                    company_id=company_id,
                    branch_id=locked.branch_id,
                    application_user_id=operator.application_user_id,
                    correlation_id=operation.correlation_id,
                    reason=reason,
                    previous_values={"status": DRAFT},
                    new_values={"status": CANCELLED, "operation_id": operation.id},
                )
                self._repo.commit()
                return PurchaseView(locked, self._repo.lines(locked.id), None)

            if locked.status != CONFIRMED:
                raise InvalidStatusError(locked.status)
            self._repo.add(operation)
            self._repo.flush()
            self._repo.commit()
        except IntegrityError as error:
            self._repo.rollback()
            constraint = violated_constraint(error)
            if constraint == UQ_IDEMPOTENCY_KEY:
                replayed = self._keys.existing_key(idempotency_key, company_id, purchase_id, CANCEL, actor)
                if replayed is not None:
                    return replayed
            if constraint == UQ_PENDING:
                pending = self._repo.pending_operation(purchase_id)
                raise OperationInProgressError(pending.id if pending else "") from None
            raise
        except Exception:
            self._repo.rollback()
            raise

        return self._engine.run_cancellation(operation.id, actor.subject)
