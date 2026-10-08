"""Repositorio de Sales Service (`data-model.md`; research.md R-03 a R-05, R-16, R-18).

Orden de bloqueo en todos los flujos: venta → operación → contador de secuencia
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

from sales_service.domain.status import PENDING
from sales_service.infrastructure.database import set_lock_timeout
from sales_service.infrastructure.models import (
    Sale,
    SaleDetail,
    SaleOperation,
)

UQ_IDEMPOTENCY_KEY = "uq_sale_operations_idempotency_key"
UQ_PENDING = "uq_sale_operations_pending"


def violated_constraint(error: IntegrityError) -> str | None:
    """Nombre de la restricción violada (psycopg 3)."""
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None)


@dataclass(frozen=True, slots=True)
class Page:
    items: list
    total_records: int


class SaleRepository:
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

    # ---------------------------------------------------------------- ventas

    def get_sale(self, company_id: UUID, sale_id: UUID) -> Sale | None:
        return self.session.scalars(
            select(Sale)
            .where(Sale.id == sale_id, Sale.company_id == company_id)
            .execution_options(populate_existing=True)
        ).one_or_none()

    def lock_sale(self, company_id: UUID, sale_id: UUID) -> Sale | None:
        return self.session.scalars(
            select(Sale)
            .where(Sale.id == sale_id, Sale.company_id == company_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one_or_none()

    def lines(self, sale_id: UUID) -> list[SaleDetail]:
        return list(
            self.session.scalars(
                select(SaleDetail)
                .where(SaleDetail.sale_id == sale_id)
                .order_by(SaleDetail.line_number)
                .execution_options(populate_existing=True)
            )
        )

    def lines_of(self, sale_ids: Sequence[UUID]) -> dict[UUID, list[SaleDetail]]:
        result: dict[UUID, list[SaleDetail]] = {sale_id: [] for sale_id in sale_ids}
        if not sale_ids:
            return result
        for line in self.session.scalars(
            select(SaleDetail)
            .where(SaleDetail.sale_id.in_(sale_ids))
            .order_by(SaleDetail.sale_id, SaleDetail.line_number)
        ):
            result[line.sale_id].append(line)
        return result

    def add(self, entity) -> None:
        self.session.add(entity)

    def add_all(self, entities) -> None:
        self.session.add_all(entities)

    def delete(self, entity) -> None:
        self.session.delete(entity)

    def flush(self) -> None:
        self.session.flush()

    def list_sales(
        self,
        company_id: UUID,
        *,
        status: str | None,
        branch_id: UUID | None,
        customer_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        number: str | None,
        page: int,
        page_size: int,
    ) -> Page:
        conditions = [Sale.company_id == company_id]
        if status:
            conditions.append(Sale.status == status)
        if branch_id:
            conditions.append(Sale.branch_id == branch_id)
        if customer_id:
            conditions.append(Sale.company_customer_id == customer_id)
        if date_from:
            conditions.append(Sale.operation_date >= date_from)
        if date_to:
            conditions.append(Sale.operation_date <= date_to)
        if number:
            conditions.append(Sale.number == number)
        where = and_(*conditions)
        total = self.session.scalar(select(func.count()).select_from(Sale).where(where)) or 0
        items = list(
            self.session.scalars(
                select(Sale)
                .where(where)
                .order_by(Sale.operation_date.desc(), Sale.created_at.desc(), Sale.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return Page(items, total)

    # ------------------------------------------------------------ operaciones

    def operation_by_key(self, idempotency_key: str) -> SaleOperation | None:
        return self.session.scalars(
            select(SaleOperation)
            .where(SaleOperation.idempotency_key == idempotency_key)
            .execution_options(populate_existing=True)
        ).one_or_none()

    def pending_operation(self, sale_id: UUID) -> SaleOperation | None:
        return self.session.scalars(
            select(SaleOperation).where(
                SaleOperation.sale_id == sale_id, SaleOperation.status == PENDING
            )
        ).one_or_none()

    def pending_operation_ids(self, sale_ids: Sequence[UUID]) -> dict[UUID, UUID]:
        if not sale_ids:
            return {}
        rows = self.session.execute(
            select(SaleOperation.sale_id, SaleOperation.id).where(
                SaleOperation.sale_id.in_(sale_ids), SaleOperation.status == PENDING
            )
        )
        return {sale_id: operation_id for sale_id, operation_id in rows}

    def lock_operation(self, operation_id: UUID) -> SaleOperation | None:
        return self.session.scalars(
            select(SaleOperation)
            .where(SaleOperation.id == operation_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one_or_none()

    def get_operation(self, company_id: UUID, operation_id: UUID) -> SaleOperation | None:
        return self.session.scalars(
            select(SaleOperation).where(
                SaleOperation.id == operation_id, SaleOperation.company_id == company_id
            )
        ).one_or_none()

    def operations_of(self, sale_id: UUID) -> list[SaleOperation]:
        return list(
            self.session.scalars(
                select(SaleOperation)
                .where(SaleOperation.sale_id == sale_id)
                .order_by(SaleOperation.started_at, SaleOperation.id)
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
                    SELECT id FROM sale_operations
                     WHERE status = 'PENDING' AND updated_at < now() - make_interval(secs => :age)
                     ORDER BY updated_at
                     LIMIT :limit
                     FOR UPDATE SKIP LOCKED
                )
                UPDATE sale_operations AS operation
                   SET updated_at = clock_timestamp(), updated_by = :actor
                  FROM candidates
                 WHERE operation.id = candidates.id
             RETURNING operation.id, operation.updated_at
                """
            ),
            {"age": older_than_seconds, "limit": limit, "actor": actor},
        ).all()
        return [(row[0], row[1]) for row in rows]
