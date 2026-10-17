"""Esquemas de productos empresariales (`contracts/rest-api.md` §1)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

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


# ------------------------------------------------- spec 022, CR-1 (FR-022-80)

SEARCH_LIMIT_MAX = 100
SearchSortKey = Literal["display_name", "internal_code", "created_at"]


class SearchSort(StrictModel):
    """Orden estable de la búsqueda; el desempate final es siempre `id` en la misma dirección."""

    key: SearchSortKey = "display_name"
    direction: Literal["asc", "desc"] = "asc"


class SearchPosition(StrictModel):
    """Posición *keyset* de un elemento: valor de la clave de orden (`k`) e `id`.

    La devuelve la búsqueda en cada elemento; el consumidor la reenvía sin modificarla en `after`.
    """

    k: list[str] = Field(min_length=1, max_length=1)
    id: UUID


class CompanyProductSearchRequest(StrictModel):
    """Búsqueda progresiva (CR-1): filtros del listado, continuación *keyset* y modo evaluador."""

    search: str | None = Field(default=None, max_length=200)
    internal_code: str | None = Field(default=None, max_length=60)
    sku: str | None = Field(default=None, max_length=80)
    status: Literal["ACTIVE", "INACTIVE", "ALL"] = "ACTIVE"
    is_purchasable: bool | None = None
    is_sellable: bool | None = None
    inventory_control_enabled: bool | None = None
    company_product_ids: list[UUID] | None = Field(default=None, min_length=1)
    global_product_ids: list[UUID] | None = Field(default=None, min_length=1)
    sort: SearchSort = Field(default_factory=SearchSort)
    after: SearchPosition | None = None
    limit: int = Field(ge=1, le=SEARCH_LIMIT_MAX)

    @field_validator("search", "internal_code", "sku", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("company_product_ids", "global_product_ids")
    @classmethod
    def _unique_ids(cls, value: list[UUID] | None) -> list[UUID] | None:
        if value is None:
            return None
        unique = list(dict.fromkeys(value))
        if len(unique) > SEARCH_LIMIT_MAX:
            raise ValueError(f"Se admiten como máximo {SEARCH_LIMIT_MAX} identificadores.")
        return unique

    @model_validator(mode="after")
    def _consistent(self) -> "CompanyProductSearchRequest":
        if self.company_product_ids is not None and self.global_product_ids is not None:
            raise ValueError("Use company_product_ids o global_product_ids, no ambos.")
        if self.after is not None and self.sort.key == "created_at":
            try:
                datetime.fromisoformat(self.after.k[0])
            except ValueError as exc:
                raise ValueError("`after` no corresponde al orden `created_at`.") from exc
        return self


class CompanyProductSearchItem(CompanyProductResponse):
    """Elemento de la búsqueda: los campos del listado actual más su posición."""

    position: SearchPosition


class CompanyProductSearchResponse(BaseModel):
    """Sin `total_records` ni conteo: `has_more` indica si hay más elementos (spec 022, A-20)."""

    items: list[CompanyProductSearchItem]
    has_more: bool
