"""Esquemas del resumen de empresas del usuario (`contracts/rest-api.md` §4, FR-046)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductCounts(BaseModel):
    """Conteos de productos o clientes: `ACTIVE` e `INACTIVE`."""

    model_config = ConfigDict(populate_by_name=True)

    total: int
    ACTIVE: int
    INACTIVE: int


class SupplierCounts(ProductCounts):
    """Conteos de proveedores: además `BLOCKED`."""

    BLOCKED: int


class CompanySummaryResponse(BaseModel):
    """Una empresa del usuario con su razón social y sus conteos por estado."""

    model_config = ConfigDict(from_attributes=True)

    company_id: UUID
    company_status: str
    legal_name: str | None
    company_products: ProductCounts
    company_customers: ProductCounts | None
    company_suppliers: SupplierCounts | None
