"""Esquema `ProductOverview` de `product-overviews` (FR-022-30 a FR-022-33; contrato §4.1).

**Sin ningún campo de costo** (FR-022-15, SC-022-3). Los bloques condicionados (`presentations[].price`, `stock` y
los mínimos por sucursal) se **omiten** cuando el usuario no los puede ver; nunca se envían con `null`
(FR-022-14). Las respuestas se serializan con `exclude_unset`: solo se omite lo que no se asignó.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReferenceOut(Out):
    id: UUID
    code: str
    name: str


class CategoryOut(ReferenceOut):
    is_primary: bool


class IdentifierOut(Out):
    type: str
    value: str
    is_primary: bool
    global_product_presentation_id: UUID | None


class PriceOut(Out):
    """Precio aplicable en **una sola** lista (FR-022-33). Sin precio, `unit_price = null` con la `resolution` de CR."""

    price_list_id: UUID | None
    price_list_item_id: UUID | None
    unit_price: str | None
    currency_code: str | None
    resolution: str = Field(description="`PRICE_LIST_ITEM`, `NO_PRICE_IN_LIST`, `NO_APPLICABLE_PRICE_LIST` o "
                                        "`PRICE_LIST_NOT_APPLICABLE`, tal como los informa Commercial Relationship.")


class PresentationOut(Out):
    company_product_presentation_id: UUID
    global_product_presentation_id: UUID
    code: str | None
    name: str | None
    sku: str | None
    internal_code: str | None
    status: str
    is_sellable: bool
    base_quantity_factor: str | None = Field(description="Unidades base por presentación, con 4 decimales.")


class ProductPresentationOut(PresentationOut):
    price: PriceOut | None = Field(default=None, description="Solo con `perm:commercial-relationship:price_list_items:read`.")


class BranchStockOut(Out):
    branch_id: UUID
    base_quantity: str = Field(description="Cantidad en la unidad base, con 4 decimales.")
    balance_state: Literal["REGISTERED", "NOT_REGISTERED"]
    minimum_stock: str | None = Field(default=None, description="Solo con `perm:inventory:product-policies:read`.")
    minimum_state: Literal["NO_POLICY", "BELOW_MINIMUM", "AT_MINIMUM", "ABOVE_MINIMUM"] | None = Field(
        default=None, description="Solo con `perm:inventory:product-policies:read`.")


class EquivalenceOut(Out):
    company_product_presentation_id: UUID
    whole_units: int
    remainder_base_quantity: str


class StockOut(Out):
    """Existencias del producto en su unidad base; nunca se repiten por presentación (RC-022-5)."""

    base_unit: ReferenceOut | None
    total_base_quantity: str
    branches: list[BranchStockOut]
    equivalences: list[EquivalenceOut]


class ProductIdentity(Out):
    company_product_id: UUID
    global_product_id: UUID
    display_name: str
    canonical_name: str | None
    internal_code: str
    reference_code: str | None
    status: str
    global_status: str | None
    product_type: str | None
    brand: ReferenceOut | None
    categories: list[CategoryOut]
    identifiers: list[IdentifierOut]
    base_unit: ReferenceOut | None
    has_image: bool
    asset_id: UUID | None = Field(
        description="Activo de la imagen principal en Product Catalog (`/products/{global_product_id}/assets/{asset_id}`), o `null`."
    )
    image_url: str | None = Field(
        description="URL pública firmada de la imagen principal, lista para `<img src>`; `null` sin imagen o con la ruta pública deshabilitada."
    )


class ProductOverview(ProductIdentity):
    presentations: list[ProductPresentationOut]
    stock: StockOut | None = Field(default=None, description="Solo con `perm:product-inventory-query:stock:read`.")
