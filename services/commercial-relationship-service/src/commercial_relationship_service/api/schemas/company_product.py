"""Esquemas de productos empresariales (`contracts/rest-api.md` §1)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from commercial_relationship_service.api.schemas.common import (
    AuditedResponse,
    CurrencyCode,
    DisplayName,
    InternalCode,
    PercentageOut,
    ReferenceCode,
    ShortName,
    StrictModel,
    UpdateModel,
)


class CompanyProductCreate(StrictModel):
    """Adopción (FR-010). Sin precio ni costo (spec 019): enviarlos responde `422`."""

    global_product_id: UUID
    internal_code: InternalCode
    reference_code: ReferenceCode = None
    display_name: DisplayName
    short_name: ShortName = None
    currency_code: CurrencyCode
    inventory_control_enabled: bool = True
    lot_tracking_enabled: bool = False
    expiration_tracking_enabled: bool = False
    is_purchasable: bool = True
    is_sellable: bool = True


class CompanyProductUpdate(UpdateModel):
    """`PUT` (FR-015, DS-17): reemplaza los campos modificables."""

    immutable_fields = frozenset({"global_product_id", "company_id", "status"})

    internal_code: InternalCode
    reference_code: ReferenceCode = None
    display_name: DisplayName
    short_name: ShortName = None
    currency_code: CurrencyCode
    inventory_control_enabled: bool
    lot_tracking_enabled: bool
    expiration_tracking_enabled: bool
    is_purchasable: bool
    is_sellable: bool


class CompanyProductResponse(AuditedResponse):
    """Representación de un producto empresarial; sin datos del producto global."""

    global_product_id: UUID
    internal_code: str
    reference_code: str | None
    display_name: str
    short_name: str | None
    currency_code: str
    inventory_control_enabled: bool
    lot_tracking_enabled: bool
    expiration_tracking_enabled: bool
    is_purchasable: bool
    is_sellable: bool
    # Spec 021 (FR-021-07): `null` = sin configurar; se modifica solo con `.../purchase-tax`.
    purchase_tax_percentage: PercentageOut | None = None


class BatchLookupRequest(StrictModel):
    """Consulta por lotes (FR-062): de 1 a 100 UUID; el límite se valida tras quitar duplicados."""

    ids: list[UUID] = Field(min_length=1)


class BatchLookupItem(BaseModel):
    """Elemento del lote: solo `id` y `found` si no existe o está fuera del alcance."""

    id: UUID
    found: bool
    company_id: UUID | None = None
    global_product_id: UUID | None = None
    internal_code: str | None = None
    display_name: str | None = None
    currency_code: str | None = None
    inventory_control_enabled: bool | None = None
    lot_tracking_enabled: bool | None = None
    expiration_tracking_enabled: bool | None = None
    is_purchasable: bool | None = None
    is_sellable: bool | None = None
    purchase_tax_percentage: PercentageOut | None = None  # spec 021: lo usa Purchase
    status: str | None = None
    version: int | None = None


class BatchLookupResponse(BaseModel):
    items: list[BatchLookupItem]
