"""Esquemas de presentaciones empresariales (`contracts/rest-api.md` §1 de la 010)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from commercial_relationship_service.api.schemas.common import (
    AuditedResponse,
    PresentationCode,
    ReferenceCode,
    StrictModel,
    UpdateModel,
)


class CompanyProductPresentationCreate(StrictModel):
    """Adopción (FR-010)."""

    company_product_id: UUID
    global_product_presentation_id: UUID
    internal_code: PresentationCode = None
    sku: PresentationCode = None
    reference_code: ReferenceCode = None
    is_purchasable: bool = True
    is_sellable: bool = True
    is_default_purchase: bool = False
    is_default_sale: bool = False


class CompanyProductPresentationUpdate(UpdateModel):
    """`PUT` (FR-014): reemplaza los campos modificables."""

    immutable_fields = frozenset(
        {"company_product_id", "global_product_presentation_id", "company_id", "status"}
    )

    internal_code: PresentationCode = None
    sku: PresentationCode = None
    reference_code: ReferenceCode = None
    is_purchasable: bool
    is_sellable: bool
    is_default_purchase: bool
    is_default_sale: bool


class CompanyProductPresentationResponse(AuditedResponse):
    """Representación; sin datos de la presentación global (FR-017)."""

    company_product_id: UUID
    global_product_presentation_id: UUID
    internal_code: str | None
    sku: str | None
    reference_code: str | None
    is_purchasable: bool
    is_sellable: bool
    is_default_purchase: bool
    is_default_sale: bool


class PresentationBatchLookupRequest(StrictModel):
    """Consulta por lotes (FR-081): de 1 a 100 UUID tras quitar duplicados."""

    ids: list[UUID] = Field(min_length=1)


class PresentationBatchLookupItem(BaseModel):
    """Elemento del lote: solo `id` y `found` si no existe o está fuera del alcance."""

    id: UUID
    found: bool
    company_id: UUID | None = None
    company_product_id: UUID | None = None
    global_product_presentation_id: UUID | None = None
    is_purchasable: bool | None = None
    is_sellable: bool | None = None
    is_default_purchase: bool | None = None
    is_default_sale: bool | None = None
    status: str | None = None
    version: int | None = None


class PresentationBatchLookupResponse(BaseModel):
    items: list[PresentationBatchLookupItem]
