"""Esquemas de productos de proveedor (`contracts/rest-api.md` §2 de la 010)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from commercial_relationship_service.api.schemas.common import (
    AuditedResponse,
    Cost,
    CurrencyCode,
    LeadTimeHours,
    LeadTimeHoursOut,
    PackQuantity,
    Priority,
    Quantity,
    QuantityOut,
    StrictModel,
    SupplierProductCode,
    UpdateModel,
)


class _SupplierProductFields(StrictModel):
    company_product_presentation_id: UUID | None = None
    supplier_product_code: SupplierProductCode = None
    purchase_unit_id: UUID
    minimum_order_quantity: Quantity = Decimal("0")
    pack_quantity: PackQuantity = Decimal("1")
    negotiated_unit_cost: Cost | None = None
    currency_code: CurrencyCode
    expected_supplier_lead_time_hours: LeadTimeHours | None = None
    priority: Priority | None = None
    is_preferred: bool = False


class SupplierProductCreate(_SupplierProductFields):
    """Registro (FR-020)."""

    company_supplier_id: UUID
    company_product_id: UUID


class SupplierProductUpdate(_SupplierProductFields, UpdateModel):
    """`PUT` (FR-026): proveedor y producto empresarial inmutables."""

    immutable_fields = frozenset({"company_supplier_id", "company_product_id", "company_id", "status"})

    minimum_order_quantity: Quantity
    pack_quantity: PackQuantity
    is_preferred: bool


class SupplierProductResponse(AuditedResponse):
    company_supplier_id: UUID
    company_product_id: UUID
    company_product_presentation_id: UUID | None
    supplier_product_code: str | None
    purchase_unit_id: UUID
    minimum_order_quantity: QuantityOut
    pack_quantity: QuantityOut
    negotiated_unit_cost: QuantityOut | None
    currency_code: str
    expected_supplier_lead_time_hours: LeadTimeHoursOut | None
    priority: int | None
    is_preferred: bool
