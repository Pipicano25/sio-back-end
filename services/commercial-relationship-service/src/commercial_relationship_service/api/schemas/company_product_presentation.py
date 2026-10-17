"""Esquemas de presentaciones empresariales (`contracts/rest-api.md` §1 de la 010)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

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
    # Spec 022 (CR-2, FR-022-81): campos aditivos; los anteriores no cambian.
    internal_code: str | None = None
    sku: str | None = None
    reference_code: str | None = None


class PresentationBatchLookupResponse(BaseModel):
    items: list[PresentationBatchLookupItem]


# ------------------------------------------------- spec 022, CR-2 (FR-022-81)

BY_PRODUCTS_LIMIT = 100


class PresentationsByProductsRequest(StrictModel):
    """Presentaciones de 1 a 100 productos de la empresa; el límite se valida tras quitar duplicados."""

    company_product_ids: list[UUID] = Field(min_length=1)
    status: Literal["ACTIVE", "INACTIVE", "ALL"] = "ALL"

    @field_validator("company_product_ids")
    @classmethod
    def _unique(cls, value: list[UUID]) -> list[UUID]:
        unique = list(dict.fromkeys(value))
        if len(unique) > BY_PRODUCTS_LIMIT:
            raise ValueError(f"Se admiten como máximo {BY_PRODUCTS_LIMIT} productos.")
        return unique


class PresentationByProductItem(BaseModel):
    """Presentación con los campos del lote actual más sus códigos (spec 022)."""

    model_config = {"from_attributes": True}

    id: UUID
    company_id: UUID
    company_product_id: UUID
    global_product_presentation_id: UUID
    internal_code: str | None
    sku: str | None
    reference_code: str | None
    is_purchasable: bool
    is_sellable: bool
    is_default_purchase: bool
    is_default_sale: bool
    status: str
    version: int


class PresentationsByProductsResponse(BaseModel):
    items: list[PresentationByProductItem]
