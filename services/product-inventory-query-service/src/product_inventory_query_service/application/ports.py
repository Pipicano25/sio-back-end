"""Puertos de las integraciones (Principio XV; `contracts/dependencies.md` de la spec 022).

Los adaptadores HTTP viven en `infrastructure/`; las pruebas los sustituyen por dobles. Los objetos que
devuelven ya están validados y **nunca** traen costos: el adaptador de Inventory descarta `inventory_value`
y `average_unit_cost` de los saldos (FR-022-15).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

Position = dict[str, Any]
"""Posición *keyset* opaca que entrega un conductor; se reenvía sin modificarla (research R-06)."""


# --------------------------------------------------------------------------- Operational Context


@dataclass(frozen=True, slots=True)
class BranchInfo:
    id: UUID
    company_id: UUID
    status: str


class OperationalContextPort(Protocol):
    """Siempre con el token del usuario (D5, research R-02)."""

    async def has_company_access(self, company_id: UUID) -> bool:
        """`operational-access?company_id=`: `True` solo con membresía `ACTIVE` (o empresa inexistente → `False`)."""

    async def branches(self, company_id: UUID, *, status: str) -> list[BranchInfo]:
        """Sucursales de la empresa en ese estado (`ACTIVE` o `INACTIVE`), siguiendo todas las páginas."""


# --------------------------------------------------------------------------- Commercial Relationship


@dataclass(frozen=True, slots=True)
class CompanyProduct:
    id: UUID
    company_id: UUID
    global_product_id: UUID
    internal_code: str
    reference_code: str | None
    display_name: str
    status: str
    is_sellable: bool
    is_purchasable: bool
    inventory_control_enabled: bool
    created_at: datetime
    position: Position = field(default_factory=dict, compare=False)


@dataclass(frozen=True, slots=True)
class CompanyPresentation:
    id: UUID
    company_id: UUID
    company_product_id: UUID
    global_product_presentation_id: UUID
    internal_code: str | None
    sku: str | None
    reference_code: str | None
    is_sellable: bool
    status: str


@dataclass(frozen=True, slots=True)
class PriceLine:
    company_product_id: UUID
    company_product_presentation_id: UUID
    price_list_id: UUID | None


@dataclass(frozen=True, slots=True)
class PriceResult:
    company_product_presentation_id: UUID
    resolution: str
    unit_price: str | None
    currency_code: str | None
    price_list_id: UUID | None
    price_list_item_id: UUID | None


@dataclass(frozen=True, slots=True)
class ProductCriteria:
    """Filtros comerciales de CR-1."""

    status: str = "ACTIVE"
    search: str | None = None
    internal_code: str | None = None
    sku: str | None = None
    inventory_control_enabled: bool | None = None


class CommercialRelationshipPort(Protocol):
    """Identidad técnica con `platform:lookup` (FR-022-100)."""

    async def search_products(
        self,
        company_id: UUID,
        criteria: ProductCriteria,
        *,
        sort_key: str,
        descending: bool,
        limit: int,
        after: Position | None = None,
        company_product_ids: list[UUID] | None = None,
        global_product_ids: list[UUID] | None = None,
    ) -> tuple[list[CompanyProduct], bool]:
        """CR-1: productos en orden con su `position` y `has_more`."""

    async def presentations_by_products(self, company_id: UUID, company_product_ids: list[UUID]) -> list[CompanyPresentation]:
        """CR-2: todas las presentaciones de esos productos (hasta 100 productos por llamada)."""

    async def resolve_prices(self, company_id: UUID, lines: list[PriceLine]) -> list[PriceResult]:
        """Precio aplicable de las líneas, en lotes de 100."""

    async def count_adopted(self, company_id: UUID) -> int:
        """Productos `ACTIVE` con control de inventario (`total_records` del listado actual)."""


# --------------------------------------------------------------------------- Product Catalog


@dataclass(frozen=True, slots=True)
class Reference:
    id: UUID
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class Category(Reference):
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class Identifier:
    type: str
    value: str
    is_primary: bool
    global_product_presentation_id: UUID | None


@dataclass(frozen=True, slots=True)
class ProductSummary:
    id: UUID
    canonical_name: str
    product_type: str
    status: str
    brand: Reference | None
    base_unit: Reference | None
    categories: tuple[Category, ...]
    identifiers: tuple[Identifier, ...]
    has_image: bool
    image_url: str | None


@dataclass(frozen=True, slots=True)
class PresentationInfo:
    """Presentación global (`presentations/batch-lookup` existente, spec 021): código, nombre y factor."""

    id: UUID
    global_product_id: UUID
    code: str
    name: str
    status: str
    base_quantity: Decimal | None


@dataclass(frozen=True, slots=True)
class CatalogFilters:
    """Filtros de catálogo de PC-2."""

    brand_ids: tuple[UUID, ...] = ()
    category_ids: tuple[UUID, ...] = ()
    include_descendants: bool = False
    identifier: str | None = None
    product_type: str | None = None
    has_image: bool | None = None
    status: str = "ALL"


class ProductCatalogPort(Protocol):
    async def summaries(self, ids: list[UUID]) -> dict[UUID, ProductSummary]:
        """PC-1: solo los encontrados (hasta 100 por llamada)."""

    async def match_candidates(self, filters: CatalogFilters, candidate_ids: list[UUID]) -> list[UUID]:
        """PC-2 en modo evaluador."""

    async def match_page(
        self, filters: CatalogFilters, *, limit: int, after: Position | None = None
    ) -> tuple[list[tuple[UUID, Position]], bool]:
        """PC-2 en modo conductor."""

    async def units(self, ids: list[UUID]) -> dict[UUID, Reference]:
        """PC-3: código y nombre de las unidades encontradas."""

    async def presentations(self, ids: list[UUID]) -> dict[UUID, PresentationInfo]:
        """`presentations/batch-lookup` (existente): solo las encontradas (hasta 100 por llamada)."""


# --------------------------------------------------------------------------- Inventory


@dataclass(frozen=True, slots=True)
class Balance:
    """Saldo sin costo: el adaptador descarta `inventory_value` y `average_unit_cost`."""

    company_product_id: UUID
    branch_id: UUID
    quantity: Decimal
    registered: bool


@dataclass(frozen=True, slots=True)
class Policy:
    company_product_id: UUID
    branch_id: UUID
    minimum_stock: Decimal


@dataclass(frozen=True, slots=True)
class BelowMinimumPair:
    company_product_id: UUID
    branch_id: UUID
    base_quantity: Decimal
    minimum_stock: Decimal
    shortfall: Decimal
    position: Position = field(default_factory=dict, compare=False)


@dataclass(frozen=True, slots=True)
class SummaryCounts:
    products_with_positive_balance: int
    products_with_zero_balance: int
    products_with_policy: int
    products_below_minimum: int


@dataclass(frozen=True, slots=True)
class InventorySummary:
    branches: dict[UUID, SummaryCounts]
    consolidated: SummaryCounts


class InventoryPort(Protocol):
    async def balances(self, company_id: UUID, branch_id: UUID, ids: list[UUID]) -> dict[UUID, Balance]:
        """`balances/lookup` (existente), un elemento por id, sin costos."""

    async def policies(self, company_id: UUID, branch_id: UUID, ids: list[UUID]) -> dict[UUID, Policy]:
        """INV-1: solo las políticas activas."""

    async def product_set(
        self,
        company_id: UUID,
        branch_ids: list[UUID],
        *,
        stock_state: str | None,
        minimum_state: str | None,
        limit: int,
        after: Position | None = None,
    ) -> tuple[list[tuple[UUID, Position]], bool]:
        """INV-2 en modo productos."""

    async def below_minimum_pairs(
        self, company_id: UUID, branch_ids: list[UUID], *, limit: int, after: Position | None = None
    ) -> tuple[list[BelowMinimumPair], bool]:
        """INV-2 en modo pares (`BELOW_MINIMUM`)."""

    async def summary(self, company_id: UUID, branch_ids: list[UUID]) -> InventorySummary:
        """INV-3."""


class TokenProvider(Protocol):
    async def token(self) -> str:
        """Token técnico vigente (renovado antes de vencer)."""

    def invalidate(self) -> None:
        """Descarta el token en caché (tras un `401`)."""
