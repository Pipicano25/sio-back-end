"""Esquemas de la adopción masiva (`specs/027-bulk-product-adoption/contracts/bulk-adoption.md` §1).

Los datos propios por elemento reutilizan los tipos de `CompanyProductCreate` y `CompanyProductPresentationCreate`,
todos opcionales: lo que falta se completa con `defaults` y con los valores automáticos (research R5 y R6).

`mode=PRODUCTS` está en el contrato, pero es la Historia 2: por ahora responde `422 VALIDATION_ERROR` con un
mensaje que lo indica.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from commercial_relationship_service.api.schemas.common import (
    CurrencyCode,
    DisplayName,
    InternalCode,
    PresentationCode,
    ReferenceCode,
    ShortName,
    StrictModel,
)
from commercial_relationship_service.application.bulk_adoption_service import BULK_LIMIT

BulkAdoptionMode = Literal["PRESENTATIONS", "PRODUCTS"]
BulkResult = Literal["ADOPTED", "ALREADY_ADOPTED", "REJECTED"]
BulkReason = Literal[
    "GLOBAL_NOT_FOUND",
    "GLOBAL_INACTIVE",
    "NOT_ELIGIBLE",
    "DUPLICATE_INTERNAL_CODE",
    "DUPLICATE_SKU",
    "COMPANY_PRODUCT_INACTIVE",
    "PRODUCT_REJECTED",
    "PRODUCT_MISMATCH",
    "PRODUCT_DATA_CONFLICT",
    "DEPENDENCY_UNAVAILABLE",
]


class _SentValues(StrictModel):
    def sent(self) -> dict[str, Any]:
        """Solo los campos con valor: los ausentes o `null` se completan con los automáticos."""
        return self.model_dump(exclude_none=True)


class BulkAdoptionDefaults(_SentValues):
    """Moneda y banderas para los productos que no las traen. Sin enviar: `COP` y los de la adopción individual."""

    currency_code: CurrencyCode | None = None
    inventory_control_enabled: bool | None = None
    lot_tracking_enabled: bool | None = None
    expiration_tracking_enabled: bool | None = None
    is_purchasable: bool | None = None
    is_sellable: bool | None = None


class BulkProductValues(_SentValues):
    """Datos propios del producto en la empresa (campos de `CompanyProductCreate` sin `global_product_id`)."""

    internal_code: InternalCode | None = None
    reference_code: ReferenceCode = None
    display_name: DisplayName | None = None
    short_name: ShortName = None
    currency_code: CurrencyCode | None = None
    inventory_control_enabled: bool | None = None
    lot_tracking_enabled: bool | None = None
    expiration_tracking_enabled: bool | None = None
    is_purchasable: bool | None = None
    is_sellable: bool | None = None


class BulkPresentationValues(_SentValues):
    """Datos propios de la presentación (campos de `CompanyProductPresentationCreate` sin los ids)."""

    internal_code: PresentationCode = None
    sku: PresentationCode = None
    reference_code: ReferenceCode = None
    is_purchasable: bool | None = None
    is_sellable: bool | None = None
    is_default_purchase: bool | None = None
    is_default_sale: bool | None = None


class BulkAdoptionItem(StrictModel):
    """Elemento de la lista: con `PRESENTATIONS`, `global_product_presentation_id` (obligatorio)."""

    global_product_presentation_id: UUID | None = None
    global_product_id: UUID | None = Field(default=None, description="Solo con `mode=PRODUCTS` (Historia 2).")
    product: BulkProductValues | None = None
    presentation: BulkPresentationValues | None = None


class BulkAdoptionRequest(StrictModel):
    """Adopción en espera de 1 a 100 elementos distintos (FR-003); los ids repetidos se procesan una vez."""

    mode: BulkAdoptionMode
    defaults: BulkAdoptionDefaults | None = None
    items: list[BulkAdoptionItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> "BulkAdoptionRequest":
        if self.mode == "PRODUCTS":
            raise ValueError(
                "El modo PRODUCTS todavía no está disponible; use PRESENTATIONS con las presentaciones a adoptar."
            )

        for position, item in enumerate(self.items):
            if item.global_product_presentation_id is None or item.global_product_id is not None:
                raise ValueError(
                    f"items[{position}]: con mode=PRESENTATIONS envíe global_product_presentation_id y no "
                    "global_product_id."
                )

        if len({item.global_product_presentation_id for item in self.items}) > BULK_LIMIT:
            raise ValueError(f"Se admiten como máximo {BULK_LIMIT} elementos distintos por solicitud.")

        return self


class BulkCounts(BaseModel):
    adopted: int
    already_adopted: int
    rejected: int


class BulkTotals(BaseModel):
    products: BulkCounts
    presentations: BulkCounts


class BulkProductResult(BaseModel):
    """Resultado de un producto: el adoptado o el que ya existía (`company_product_id`), o el motivo del rechazo."""

    global_product_id: UUID
    company_product_id: UUID | None
    internal_code: str | None
    result: BulkResult
    reason: BulkReason | None


class BulkPresentationResult(BaseModel):
    """Resultado de una presentación; `global_product_id` es `null` si la presentación global no existe."""

    global_product_presentation_id: UUID
    global_product_id: UUID | None
    company_product_presentation_id: UUID | None
    result: BulkResult
    reason: BulkReason | None


class BulkAdoptionResponse(BaseModel):
    """Siempre `200` con una solicitud válida, aunque haya elementos rechazados."""

    company_id: UUID
    mode: BulkAdoptionMode
    totals: BulkTotals
    products: list[BulkProductResult]
    presentations: list[BulkPresentationResult]
