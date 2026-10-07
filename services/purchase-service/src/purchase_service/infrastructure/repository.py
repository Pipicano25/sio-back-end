"""Repositorio de Purchase Service (`data-model.md`; research.md R-03 a R-05, R-10, R-16).

Orden de bloqueo en todos los flujos: compra → operación → contador de secuencia
(sin interbloqueos). Las transacciones las confirman o revierten los servicios de
aplicación; aquí solo se consulta, bloquea y modifica dentro de la transacción en curso.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from purchase_service.domain.status import PENDING
from purchase_service.infrastructure.database import set_lock_timeout
from purchase_service.infrastructure.models import (
    Purchase,
    PurchaseDetail,
    PurchaseLifecycleEvent,
    PurchaseOperation,
)

UQ_IDEMPOTENCY_KEY = "uq_purchase_operations_idempotency_key"
UQ_PENDING = "uq_purchase_operations_pending"


def violated_constraint(error: IntegrityError) -> str | None:
    """Nombre de la restricción violada (psycopg 3)."""
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None)


@dataclass(frozen=True, slots=True)
class Page:
    items: list
    total_records: int


class PurchaseRepository:
    def __init__(self, session: Session, *, lock_timeout_ms: int) -> None:
        self.session = session
        self._lock_timeout_ms = lock_timeout_ms

    # ------------------------------------------------------------ transacción

    def begin(self) -> None:
        """Fija `lock_timeout` para la transacción que empieza (R-05)."""
        set_lock_timeout(self.session, self._lock_timeout_ms)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def end_read(self) -> None:
        """Cierra la transacción de solo lectura antes de llamar a la red (sin expirar objetos)."""
        self.session.commit()

    # ---------------------------------------------------------------- compras

    def get_purchase(self, company_id: UUID, purchase_id: UUID) -> Purchase | None:
        return self.session.scalars(
            select(Purchase)
            .where(Purchase.id == purchase_id, Purchase.company_id == company_id)
            .execution_options(populate_existing=True)
        ).one_or_none()

    def lock_purchase(self, company_id: UUID, purchase_id: UUID) -> Purchase | None:
        return self.session.scalars(
            select(Purchase)
            .where(Purchase.id == purchase_id, Purchase.company_id == company_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one_or_none()

    def lines(self, purchase_id: UUID) -> list[PurchaseDetail]:
        return list(
            self.session.scalars(
                select(PurchaseDetail)
                .where(PurchaseDetail.purchase_id == purchase_id)
                .order_by(PurchaseDetail.line_number)
                .execution_options(populate_existing=True)
            )
        )

    def lines_of(self, purchase_ids: Sequence[UUID]) -> dict[UUID, list[PurchaseDetail]]:
        result: dict[UUID, list[PurchaseDetail]] = {purchase_id: [] for purchase_id in purchase_ids}
        if not purchase_ids:
            return result
        for line in self.session.scalars(
            select(PurchaseDetail)
            .where(PurchaseDetail.purchase_id.in_(purchase_ids))
            .order_by(PurchaseDetail.purchase_id, PurchaseDetail.line_number)
        ):
            result[line.purchase_id].append(line)
        return result

    def add(self, entity) -> None:
        self.session.add(entity)

    def add_all(self, entities) -> None:
        self.session.add_all(entities)

    def delete(self, entity) -> None:
        self.session.delete(entity)

    def flush(self) -> None:
        self.session.flush()

    def list_purchases(
        self,
        company_id: UUID,
        *,
        status: str | None,
        branch_id: UUID | None,
        supplier_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        number: str | None,
        page: int,
        page_size: int,
    ) -> Page:
        conditions = [Purchase.company_id == company_id]
        if status:
            conditions.append(Purchase.status == status)
        if branch_id:
            conditions.append(Purchase.branch_id == branch_id)
        if supplier_id:
            conditions.append(Purchase.company_supplier_id == supplier_id)
        if date_from:
            conditions.append(Purchase.operation_date >= date_from)
        if date_to:
            conditions.append(Purchase.operation_date <= date_to)
        if number:
            conditions.append(Purchase.number == number)
        where = and_(*conditions)
        total = self.session.scalar(select(func.count()).select_from(Purchase).where(where)) or 0
        items = list(
            self.session.scalars(
                select(Purchase)
                .where(where)
                .order_by(Purchase.operation_date.desc(), Purchase.created_at.desc(), Purchase.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return Page(items, total)

    # ------------------------------------------------------------ operaciones

    def operation_by_key(self, idempotency_key: str) -> PurchaseOperation | None:
        return self.session.scalars(
            select(PurchaseOperation)
            .where(PurchaseOperation.idempotency_key == idempotency_key)
            .execution_options(populate_existing=True)
        ).one_or_none()

    def pending_operation(self, purchase_id: UUID) -> PurchaseOperation | None:
        return self.session.scalars(
            select(PurchaseOperation).where(
                PurchaseOperation.purchase_id == purchase_id, PurchaseOperation.status == PENDING
            )
        ).one_or_none()

    def pending_operation_ids(self, purchase_ids: Sequence[UUID]) -> dict[UUID, UUID]:
        if not purchase_ids:
            return {}
        rows = self.session.execute(
            select(PurchaseOperation.purchase_id, PurchaseOperation.id).where(
                PurchaseOperation.purchase_id.in_(purchase_ids), PurchaseOperation.status == PENDING
            )
        )
        return {purchase_id: operation_id for purchase_id, operation_id in rows}

    def lock_operation(self, operation_id: UUID) -> PurchaseOperation | None:
        return self.session.scalars(
            select(PurchaseOperation)
            .where(PurchaseOperation.id == operation_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one_or_none()

    def get_operation(self, company_id: UUID, operation_id: UUID) -> PurchaseOperation | None:
        return self.session.scalars(
            select(PurchaseOperation).where(
                PurchaseOperation.id == operation_id, PurchaseOperation.company_id == company_id
            )
        ).one_or_none()

    def operations_of(self, purchase_id: UUID) -> list[PurchaseOperation]:
        return list(
            self.session.scalars(
                select(PurchaseOperation)
                .where(PurchaseOperation.purchase_id == purchase_id)
                .order_by(PurchaseOperation.started_at, PurchaseOperation.id)
            )
        )

    def claim_stale_pending(self, older_than_seconds: float, limit: int, actor: str) -> list[tuple[UUID, object]]:
        """Toma operaciones `PENDING` antiguas (`SKIP LOCKED`), marca `updated_at` y devuelve `(id, marca)`.

        La marca (`updated_at` nuevo) permite al conciliador detectar después si otro proceso
        (un reintento del cliente) tocó la operación mientras consultaba Inventory (R-08).
        """
        rows = self.session.execute(
            text(
                """
                WITH candidates AS (
                    SELECT id FROM purchase_operations
                     WHERE status = 'PENDING' AND updated_at < now() - make_interval(secs => :age)
                     ORDER BY updated_at
                     LIMIT :limit
                     FOR UPDATE SKIP LOCKED
                )
                UPDATE purchase_operations AS operation
                   SET updated_at = clock_timestamp(), updated_by = :actor
                  FROM candidates
                 WHERE operation.id = candidates.id
             RETURNING operation.id, operation.updated_at
                """
            ),
            {"age": older_than_seconds, "limit": limit, "actor": actor},
        ).all()
        return [(row[0], row[1]) for row in rows]

    # ------------------------------------------------------------------ hitos

    def events(self, purchase_id: UUID) -> list[PurchaseLifecycleEvent]:
        return list(
            self.session.scalars(
                select(PurchaseLifecycleEvent)
                .where(PurchaseLifecycleEvent.purchase_id == purchase_id)
                .order_by(PurchaseLifecycleEvent.created_at, PurchaseLifecycleEvent.id)
            )
        )
