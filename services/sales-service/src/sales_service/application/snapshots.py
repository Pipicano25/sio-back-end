"""Aplicación de snapshots, precio, totales y costo sobre las entidades (DS-02, FR-007, FR-009, FR-019).

Los snapshots son la excepción documentada al Principio III: provisionales mientras la
venta está en `DRAFT` (se refrescan al guardar lo que cambia) y refrescados y
**congelados al confirmar**; después no se actualizan nunca. El precio también se
resuelve al guardar la línea y se verifica al confirmar (DS-05).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP

from sales_service.application.ports import MovementCost
from sales_service.application.reference_validation import HeaderSnapshot, LineSnapshot
from sales_service.domain.conversion import base_quantity
from sales_service.domain.margin import MarginResult, compute_margin
from sales_service.domain.money import MONEY_QUANTUM, QUANTITY_QUANTUM, LineAmounts, header_totals
from sales_service.domain.status import CASH
from sales_service.infrastructure.models import Sale, SaleDetail


def apply_header(sale: Sale, snapshot: HeaderSnapshot) -> None:
    sale.customer_name_snapshot = snapshot.customer_name
    sale.customer_identification_snapshot = snapshot.customer_identification
    # Spec 020 (FR-020-09): medio de pago declarado y su copia (refrescada y congelada al confirmar).
    sale.payment_method_id = snapshot.payment_method_id
    sale.payment_method_code_snapshot = snapshot.payment_method_code
    sale.payment_method_name_snapshot = snapshot.payment_method_name


def apply_business_date(sale: Sale, business_date: date) -> None:
    """Solo contado en el MVP (DP-01): `due_date = operation_date`, sin condición ni plazo (R-12)."""
    sale.operation_date = business_date
    sale.due_date = business_date
    sale.customer_payment_condition_id = None
    sale.payment_condition_code_snapshot = CASH
    sale.payment_terms_days_snapshot = 0


def apply_line(detail: SaleDetail, snapshot: LineSnapshot) -> None:
    detail.product_code_snapshot = snapshot.product_code
    detail.product_name_snapshot = snapshot.product_name
    detail.presentation_code_snapshot = snapshot.presentation_code
    detail.presentation_name_snapshot = snapshot.presentation_name
    detail.base_quantity_factor_snapshot = snapshot.factor
    detail.unit_code_snapshot = snapshot.unit_code
    detail.price_list_id = snapshot.price_list_id
    detail.price_list_item_id = snapshot.price_list_item_id
    detail.price_list_requested = snapshot.price_list_requested


def apply_amounts(detail: SaleDetail, amounts: LineAmounts) -> None:
    detail.quantity = amounts.quantity
    detail.unit_price = amounts.unit_price
    detail.discount_amount = amounts.discount_amount
    detail.tax_amount = amounts.tax_amount
    detail.subtotal = amounts.subtotal
    detail.total = amounts.total


def apply_cost(detail: SaleDetail, movement: MovementCost) -> MarginResult:
    """Costo FIFO copiado de Inventory (por unidad base, sin convertir ni recalcular; P-05) y margen (R-10)."""
    detail.unit_cost_snapshot = movement.unit_cost.quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)
    detail.cost_total = movement.movement_value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    detail.cost_known = movement.cost_known is True
    margin = compute_margin(detail.subtotal, detail.discount_amount, detail.cost_total, detail.cost_known)
    detail.gross_margin_amount = margin.amount
    detail.gross_margin_percentage = margin.percentage
    return margin


def recompute_totals(sale: Sale, lines: list[SaleDetail]) -> None:
    totals = header_totals((line.subtotal, line.discount_amount, line.tax_amount) for line in lines)
    sale.subtotal = totals.subtotal
    sale.discount_total = totals.discount_total
    sale.tax_total = totals.tax_total
    sale.total = totals.total


def touch(entity, actor: str, now: datetime) -> None:
    entity.updated_at = now
    entity.updated_by = actor


def line_base_quantity(detail: SaleDetail):
    return base_quantity(detail.quantity, detail.base_quantity_factor_snapshot)
