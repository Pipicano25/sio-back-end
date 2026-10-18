"""Consulta validada (`data-model.md` §2.1; FR-022-20, FR-022-34, FR-022-61, FR-022-65)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class Endpoint(str, Enum):
    PRODUCT_OVERVIEWS = "product-overviews"
    INVENTORY_OVERVIEWS = "inventory-overviews"
    LOW_STOCK_PRODUCTS = "low-stock-products"


SORT_KEYS = ("display_name", "internal_code", "created_at")
"""Claves de orden explícito (campos de CR)."""

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 20
MAX_CURSOR_LENGTH = 2048


@dataclass(frozen=True, slots=True)
class Sort:
    key: str
    descending: bool = False

    @property
    def text(self) -> str:
        return f"{self.key}:{'desc' if self.descending else 'asc'}"


@dataclass(frozen=True, slots=True)
class QuerySpec:
    endpoint: Endpoint
    company_id: UUID
    branch_ids: tuple[UUID, ...] | None = None
    """`None` = `scope = COMPANY`."""
    search: str | None = None
    internal_code: str | None = None
    sku: str | None = None
    barcode: str | None = None
    identifier: str | None = None
    brand_ids: tuple[UUID, ...] = ()
    category_ids: tuple[UUID, ...] = ()
    include_descendants: bool = False
    status: str = "ACTIVE"
    product_type: str | None = None
    has_image: bool | None = None
    stock_state: str | None = None
    minimum_state: str | None = None
    price_list_id: UUID | None = None
    sort: Sort | None = None
    page_size: int = DEFAULT_PAGE_SIZE
    cursor: str | None = None

    @property
    def catalog_filters(self) -> bool:
        return bool(self.brand_ids or self.category_ids or self.product_type is not None or self.has_image is not None
                    or self.barcode or self.identifier)

    @property
    def used_filters(self) -> set[str]:
        """Nombres de los filtros presentes (para la visibilidad por bloque, FR-022-14)."""
        names = set()
        for name in ("search", "internal_code", "sku", "barcode", "identifier", "product_type", "has_image",
                     "stock_state", "minimum_state", "price_list_id"):
            if getattr(self, name) is not None:
                names.add(name)
        if self.brand_ids:
            names.add("brand_id")
        if self.category_ids:
            names.add("category_id")
        return names
