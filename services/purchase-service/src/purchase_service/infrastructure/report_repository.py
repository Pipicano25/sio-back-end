"""Compras del período para reportes (spec 023, PUR-R1; solo lectura).

Compras no `DRAFT` con `operation_date` en el período (DR-02), clasificadas según DR-03:

| `category` | Regla |
|---|---|
| `RECEIVED` | `status = 'CONFIRMED'` y `received_at` informado |
| `PENDING_RECEIPT` | `status = 'CONFIRMED'` sin `received_at` (no es mercancía recibida) |
| `CANCELLED` | `status = 'CANCELLED'` (aunque se hubiera recibido antes); nunca suma en el total efectivo |

Filas sin líneas, paginadas sobre `ix_purchases_company_date`; los totales del período salen de **una** consulta
agregada con `FILTER`, por moneda (nunca se suman monedas distintas).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.orm import Session

from purchase_service.infrastructure.models import Purchase

RECEIVED = "RECEIVED"
PENDING_RECEIPT = "PENDING_RECEIPT"
CANCELLED = "CANCELLED"
CATEGORIES = (RECEIVED, PENDING_RECEIPT, CANCELLED)

_IS_CANCELLED = Purchase.status == "CANCELLED"
_IS_RECEIVED = and_(Purchase.status == "CONFIRMED", Purchase.received_at.is_not(None))
_IS_PENDING = and_(Purchase.status == "CONFIRMED", Purchase.received_at.is_(None))
CATEGORY = case((_IS_CANCELLED, literal(CANCELLED)), (_IS_RECEIVED, literal(RECEIVED)), else_=literal(PENDING_RECEIPT))
_BY_CATEGORY = {RECEIVED: _IS_RECEIVED, PENDING_RECEIPT: _IS_PENDING, CANCELLED: _IS_CANCELLED}


@dataclass(frozen=True, slots=True)
class PeriodTotals:
    currency_code: str
    received_count: int
    received_total: Decimal
    pending_receipt_count: int
    pending_receipt_total: Decimal
    cancelled_count: int
    cancelled_total: Decimal

    @property
    def effective_total(self) -> Decimal:
        return self.received_total + self.pending_receipt_total


@dataclass(frozen=True, slots=True)
class PeriodPage:
    items: list
    total_records: int
    totals: list[PeriodTotals]


class PurchaseReportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def period(self, company_id: UUID, *, date_from: date, date_to: date, branch_ids: list[UUID],
               categories: list[str], page: int, page_size: int) -> PeriodPage:
        scope = [
            Purchase.company_id == company_id,
            Purchase.status != "DRAFT",
            Purchase.operation_date >= date_from,
            Purchase.operation_date <= date_to,
        ]
        if branch_ids:
            scope.append(Purchase.branch_id.in_(branch_ids))
        rows_where = and_(*scope, or_(*(_BY_CATEGORY[c] for c in categories))) if categories else and_(*scope)
        total_records = self.session.scalar(select(func.count()).select_from(Purchase).where(rows_where)) or 0
        items = self.session.execute(
            select(
                Purchase.id, Purchase.operation_date, Purchase.received_at, Purchase.branch_id,
                Purchase.supplier_name_snapshot, Purchase.supplier_identification_snapshot, Purchase.number,
                Purchase.supplier_document_number, Purchase.status, CATEGORY.label("category"),
                Purchase.currency_code, Purchase.total,
            )
            .where(rows_where)
            .order_by(Purchase.operation_date, Purchase.number, Purchase.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        # Los totales son del período completo (sin el filtro de categoría ni la página).
        zero = literal(0)
        totals = self.session.execute(
            select(
                Purchase.currency_code,
                func.count().filter(_IS_RECEIVED).label("received_count"),
                func.coalesce(func.sum(Purchase.total).filter(_IS_RECEIVED), zero).label("received_total"),
                func.count().filter(_IS_PENDING).label("pending_count"),
                func.coalesce(func.sum(Purchase.total).filter(_IS_PENDING), zero).label("pending_total"),
                func.count().filter(_IS_CANCELLED).label("cancelled_count"),
                func.coalesce(func.sum(Purchase.total).filter(_IS_CANCELLED), zero).label("cancelled_total"),
            )
            .where(and_(*scope))
            .group_by(Purchase.currency_code)
            .order_by(Purchase.currency_code)
        ).all()
        return PeriodPage(
            items=list(items),
            total_records=total_records,
            totals=[
                PeriodTotals(row.currency_code, row.received_count, Decimal(row.received_total), row.pending_count,
                             Decimal(row.pending_total), row.cancelled_count, Decimal(row.cancelled_total))
                for row in totals
            ],
        )
