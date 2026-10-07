"""Aplicación de snapshots y totales sobre las entidades (DS-02, FR-006, FR-009).

Los snapshots son la excepción documentada al Principio III: provisionales mientras la
compra está en `DRAFT` (se refrescan al guardar lo que cambia) y refrescados y
**congelados al confirmar**; después no se actualizan nunca.
"""

from __future__ import annotations

from datetime import date, datetime

from purchase_service.application.reference_validation import HeaderSnapshot, LineSnapshot
from purchase_service.domain.conversion import base_quantity, inventory_unit_cost
from purchase_service.domain.money import LineAmounts, header_totals
from purchase_service.infrastructure.models import Purchase, PurchaseDetail


def apply_header(purchase: Purchase, snapshot: HeaderSnapshot) -> None:
    purchase.supplier_name_snapshot = snapshot.supplier_name
    purchase.supplier_identification_snapshot = snapshot.supplier_identification
    purchase.payment_condition_code_snapshot = snapshot.payment_condition_code
    purchase.payment_terms_days_snapshot = snapshot.payment_terms_days
    purchase.due_date = snapshot.due_date


def apply_line(detail: PurchaseDetail, snapshot: LineSnapshot) -> None:
    detail.product_code_snapshot = snapshot.product_code
    detail.product_name_snapshot = snapshot.product_name
    detail.presentation_code_snapshot = snapshot.presentation_code
    detail.presentation_name_snapshot = snapshot.presentation_name
    detail.base_quantity_factor_snapshot = snapshot.factor
    detail.unit_code_snapshot = snapshot.unit_code
    detail.supplier_lead_time_snapshot_hours = snapshot.lead_time_hours


def apply_amounts(detail: PurchaseDetail, amounts: LineAmounts) -> None:
    detail.quantity = amounts.quantity
    detail.unit_cost = amounts.unit_cost
    detail.discount_amount = amounts.discount_amount
    detail.tax_amount = amounts.tax_amount
    detail.subtotal = amounts.subtotal
    detail.total = amounts.total


def recompute_totals(purchase: Purchase, lines: list[PurchaseDetail]) -> None:
    totals = header_totals((line.subtotal, line.discount_amount, line.tax_amount) for line in lines)
    purchase.subtotal = totals.subtotal
    purchase.discount_total = totals.discount_total
    purchase.tax_total = totals.tax_total
    purchase.total = totals.total


def touch(entity, actor: str, now: datetime) -> None:
    entity.updated_at = now
    entity.updated_by = actor


def line_base_quantity(detail: PurchaseDetail):
    return base_quantity(detail.quantity, detail.base_quantity_factor_snapshot)


def line_inventory_cost(detail: PurchaseDetail):
    """Costo por unidad base sin impuestos que se informa a Inventory (DS-04)."""
    return inventory_unit_cost(detail.subtotal, detail.discount_amount, line_base_quantity(detail))


def due_date_of(snapshot: HeaderSnapshot) -> date:
    return snapshot.due_date
