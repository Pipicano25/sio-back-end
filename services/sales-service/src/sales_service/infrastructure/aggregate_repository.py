"""Agregaciones de ventas para reportes (spec 023, SAL-R1 y SAL-R2; solo lectura).

Ventas efectivas: `status = 'CONFIRMED'` (DR-01: las anuladas se excluyen según su estado actual y los borradores
nunca cuentan), con `operation_date` en el período (DR-02). Todo se agrupa, ordena y limita en PostgreSQL sobre
`ix_sales_company_date` y `uq_sale_details_line_number`; nada se descarga para agrupar en Python.

- Cantidad en unidad base: Σ `quantity × base_quantity_factor_snapshot` (el factor guardado al vender).
- Importe: Σ (`subtotal − discount_amount`) de las líneas; sin impuestos.
- Los importes se agrupan por `currency_code`: nunca se suman monedas distintas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session

from sales_service.infrastructure.models import Sale, SaleDetail

EFFECTIVE_STATUS = "CONFIRMED"


@dataclass(frozen=True, slots=True)
class PresentationAggregate:
    company_product_presentation_id: UUID | None
    code: str | None
    name: str | None
    quantity: Decimal
    quantity_base: Decimal
    amount: Decimal


@dataclass(frozen=True, slots=True)
class ProductAggregate:
    company_product_id: UUID
    product_code: str
    product_name: str
    currency_code: str
    quantity_base: Decimal
    amount: Decimal
    sales_count: int
    presentations: list[PresentationAggregate] | None = None


@dataclass(frozen=True, slots=True)
class CurrencyTotal:
    currency_code: str
    amount: Decimal
    sales_count: int


@dataclass(frozen=True, slots=True)
class BranchAggregate:
    branch_id: UUID
    currency_code: str
    sales_count: int
    total_amount: Decimal


class SalesAggregateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _effective(company_id: UUID, date_from: date, date_to: date, branch_ids: list[UUID]):
        conditions = [
            Sale.company_id == company_id,
            Sale.status == EFFECTIVE_STATUS,
            Sale.operation_date >= date_from,
            Sale.operation_date <= date_to,
        ]
        if branch_ids:
            conditions.append(Sale.branch_id.in_(branch_ids))
        return and_(*conditions)

    def by_product(self, company_id: UUID, *, date_from: date, date_to: date, branch_ids: list[UUID],
                   order_by: str, limit: int, include_presentations: bool) -> list[ProductAggregate]:
        where = self._effective(company_id, date_from, date_to, branch_ids)
        newest = (Sale.operation_date.desc(), Sale.created_at.desc(), SaleDetail.line_number.desc())
        quantity_base = func.sum(SaleDetail.quantity * SaleDetail.base_quantity_factor_snapshot).label("quantity_base")
        amount = func.sum(SaleDetail.subtotal - SaleDetail.discount_amount).label("amount")
        metric = quantity_base if order_by == "quantity_base" else amount
        ordering = (
            (metric.desc(), SaleDetail.company_product_id)
            if order_by == "quantity_base"
            else (Sale.currency_code, metric.desc(), SaleDetail.company_product_id)
        )
        rows = self.session.execute(
            select(
                SaleDetail.company_product_id,
                Sale.currency_code,
                quantity_base,
                amount,
                func.count(func.distinct(Sale.id)).label("sales_count"),
                # Último código y nombre del período (snapshot de la línea más reciente).
                func.array_agg(aggregate_order_by(SaleDetail.product_code_snapshot, *newest))[1].label("code"),
                func.array_agg(aggregate_order_by(SaleDetail.product_name_snapshot, *newest))[1].label("name"),
            )
            .join(Sale, Sale.id == SaleDetail.sale_id)
            .where(where)
            .group_by(SaleDetail.company_product_id, Sale.currency_code)
            .order_by(*ordering)
            .limit(limit)
        ).all()
        presentations = (
            self._presentations(where, [row.company_product_id for row in rows], newest)
            if include_presentations and rows
            else {}
        )
        return [
            ProductAggregate(
                company_product_id=row.company_product_id,
                product_code=row.code,
                product_name=row.name,
                currency_code=row.currency_code,
                quantity_base=row.quantity_base,
                amount=row.amount,
                sales_count=row.sales_count,
                presentations=presentations.get((row.company_product_id, row.currency_code), [])
                if include_presentations
                else None,
            )
            for row in rows
        ]

    def _presentations(self, where, product_ids: list[UUID], newest) -> dict[tuple[UUID, str], list]:
        rows = self.session.execute(
            select(
                SaleDetail.company_product_id,
                Sale.currency_code,
                SaleDetail.company_product_presentation_id,
                func.array_agg(aggregate_order_by(SaleDetail.presentation_code_snapshot, *newest))[1].label("code"),
                func.array_agg(aggregate_order_by(SaleDetail.presentation_name_snapshot, *newest))[1].label("name"),
                func.sum(SaleDetail.quantity).label("quantity"),
                func.sum(SaleDetail.quantity * SaleDetail.base_quantity_factor_snapshot).label("quantity_base"),
                func.sum(SaleDetail.subtotal - SaleDetail.discount_amount).label("amount"),
            )
            .join(Sale, Sale.id == SaleDetail.sale_id)
            .where(where, SaleDetail.company_product_id.in_(product_ids))
            .group_by(SaleDetail.company_product_id, Sale.currency_code, SaleDetail.company_product_presentation_id)
            .order_by(SaleDetail.company_product_id, func.sum(SaleDetail.quantity).desc(),
                      SaleDetail.company_product_presentation_id)
        ).all()
        grouped: dict[tuple[UUID, str], list[PresentationAggregate]] = {}
        for row in rows:
            grouped.setdefault((row.company_product_id, row.currency_code), []).append(
                PresentationAggregate(row.company_product_presentation_id, row.code, row.name, row.quantity,
                                      row.quantity_base, row.amount)
            )
        return grouped

    def product_totals(self, company_id: UUID, *, date_from: date, date_to: date,
                       branch_ids: list[UUID]) -> list[CurrencyTotal]:
        """Totales por moneda de todas las ventas efectivas del alcance (no solo de las filas devueltas)."""
        where = self._effective(company_id, date_from, date_to, branch_ids)
        rows = self.session.execute(
            select(
                Sale.currency_code,
                func.sum(SaleDetail.subtotal - SaleDetail.discount_amount).label("amount"),
                func.count(func.distinct(Sale.id)).label("sales_count"),
            )
            .join(Sale, Sale.id == SaleDetail.sale_id)
            .where(where)
            .group_by(Sale.currency_code)
            .order_by(Sale.currency_code)
        ).all()
        return [CurrencyTotal(row.currency_code, row.amount, row.sales_count) for row in rows]

    def by_branch(self, company_id: UUID, *, date_from: date, date_to: date,
                  branch_ids: list[UUID]) -> list[BranchAggregate]:
        where = self._effective(company_id, date_from, date_to, branch_ids)
        rows = self.session.execute(
            select(Sale.branch_id, Sale.currency_code, func.count().label("sales_count"),
                   func.sum(Sale.total).label("total_amount"))
            .where(where)
            .group_by(Sale.branch_id, Sale.currency_code)
            .order_by(Sale.currency_code, func.sum(Sale.total).desc(), Sale.branch_id)
        ).all()
        return [BranchAggregate(row.branch_id, row.currency_code, row.sales_count, row.total_amount) for row in rows]
