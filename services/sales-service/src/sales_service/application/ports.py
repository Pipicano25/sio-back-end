"""Puertos de las dependencias externas (Principio XV; `contracts/dependencies.md`).

Cada puerto tiene un único adaptador HTTP real en `infrastructure/`; las pruebas
inyectan dobles por DI. Un `get_*` devuelve `None` ante `404` del proveedor; la
indisponibilidad se expresa con `DependencyUnavailableError`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID


class TokenProvider(Protocol):
    def get_token(self) -> str: ...

    def invalidate(self) -> None: ...


# Operational Context -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CompanyInfo:
    id: UUID
    status: str
    default_currency: str


@dataclass(frozen=True, slots=True)
class BranchInfo:
    id: UUID
    company_id: UUID
    status: str
    effective_timezone: str


@dataclass(frozen=True, slots=True)
class ApplicationUserInfo:
    id: UUID
    company_id: UUID
    status: str


@dataclass(frozen=True, slots=True)
class AccessResult:
    allowed: bool
    reason: str | None
    company_id: UUID | None
    application_user_id: UUID | None


class OperationalContextDirectory(Protocol):
    def get_company(self, company_id: UUID) -> CompanyInfo | None: ...

    def get_branch(self, branch_id: UUID) -> BranchInfo | None: ...

    def get_application_user(self, application_user_id: UUID) -> ApplicationUserInfo | None: ...


class AccessDirectory(Protocol):
    """`operational-access` con el token del usuario (nunca el técnico)."""

    def check_branch(self, branch_id: UUID) -> AccessResult: ...

    def check_company(self, company_id: UUID) -> AccessResult: ...


# Commercial Relationship ---------------------------------------------------

PERSON = "PERSON"
ORGANIZATION = "ORGANIZATION"


@dataclass(frozen=True, slots=True)
class CustomerInfo:
    id: UUID
    company_id: UUID
    customer_kind: str
    person_identity_id: UUID | None
    organization_identity_id: UUID | None
    display_name: str
    status: str


@dataclass(frozen=True, slots=True)
class CompanyProductInfo:
    id: UUID
    company_id: UUID
    global_product_id: UUID
    internal_code: str
    display_name: str
    is_sellable: bool
    inventory_control_enabled: bool
    status: str


@dataclass(frozen=True, slots=True)
class CompanyPresentationInfo:
    id: UUID
    company_id: UUID
    company_product_id: UUID
    global_product_presentation_id: UUID
    is_sellable: bool
    status: str


@dataclass(frozen=True, slots=True)
class PriceRequestLine:
    """Línea de `applicable-prices/resolve`; `price_list_id` solo si el vendedor lo pidió (P-02)."""

    line_id: str
    company_product_id: UUID
    company_product_presentation_id: UUID | None
    price_list_id: UUID | None


@dataclass(frozen=True, slots=True)
class ResolvedPrice:
    """Resultado por línea de Commercial Relationship (contrato 010 §6)."""

    line_id: str
    found: bool
    resolution: str
    basis: str | None
    unit_price: Decimal | None
    currency_code: str | None
    price_list_id: UUID | None
    price_list_item_id: UUID | None


@dataclass(frozen=True, slots=True)
class PriceListInfo:
    id: UUID
    company_id: UUID
    status: str


class CommercialDirectory(Protocol):
    def get_customer(self, customer_id: UUID) -> CustomerInfo | None: ...

    def lookup_products(self, ids: Sequence[UUID]) -> dict[UUID, CompanyProductInfo]:
        """Productos encontrados (≤ 100 ids distintos); los no encontrados no aparecen."""
        ...

    def lookup_presentations(self, ids: Sequence[UUID]) -> dict[UUID, CompanyPresentationInfo]: ...

    def resolve_prices(
        self, company_id: UUID, lines: Sequence[PriceRequestLine], at: datetime
    ) -> dict[str, ResolvedPrice]:
        """`POST /companies/{c}/applicable-prices/resolve` (≤ 100 líneas), por `line_id`."""
        ...

    def get_price_list(self, price_list_id: UUID) -> PriceListInfo | None:
        """`GET /price-lists/{id}` (P-03); `404` → `None`."""
        ...


# Product Catalog -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GlobalPresentationInfo:
    id: UUID
    code: str
    name: str
    base_quantity: Decimal


@dataclass(frozen=True, slots=True)
class GlobalProductInfo:
    id: UUID
    base_unit_id: UUID


@dataclass(frozen=True, slots=True)
class UnitInfo:
    id: UUID
    code: str


class CatalogDirectory(Protocol):
    def get_presentation(self, presentation_id: UUID) -> GlobalPresentationInfo | None: ...

    def get_product(self, product_id: UUID) -> GlobalProductInfo | None: ...

    def get_unit(self, unit_id: UUID) -> UnitInfo | None: ...


# Party Identity ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IdentityInfo:
    """Persona u organización; la identificación puede faltar en una identidad existente (C-01)."""

    id: UUID
    identification_type: str | None
    identification_number: str | None


class PartyDirectory(Protocol):
    def get_person(self, person_id: UUID) -> IdentityInfo | None: ...

    def get_organization(self, organization_id: UUID) -> IdentityInfo | None: ...


# Inventory -----------------------------------------------------------------


class InventoryRejection(Exception):
    """Rechazo definitivo de Inventory (`404`, `409` o `422`): no se reintenta sin cambios."""

    def __init__(self, status: int, code: str | None, body: dict[str, Any] | None = None) -> None:
        super().__init__(code or str(status))
        self.status = status
        self.code = code
        self.body = body or {}


@dataclass(frozen=True, slots=True)
class MovementCost:
    """Costo FIFO de un movimiento de salida, tal como lo informa Inventory (P-05)."""

    origin_detail_id: UUID
    unit_cost: Decimal
    movement_value: Decimal
    cost_known: bool | None


@dataclass(frozen=True, slots=True)
class InventoryOperationRef:
    """Operación aplicada en Inventory: su `id` y, en salidas, el costo de cada movimiento."""

    id: UUID
    operation_type: str | None = None
    reverses_operation_id: UUID | None = None
    movements: tuple[MovementCost, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BalanceInfo:
    company_product_id: UUID
    quantity: Decimal


class InventoryGateway(Protocol):
    def apply_output(self, payload: dict[str, Any]) -> InventoryOperationRef:
        """`POST /inventory-outputs`; `201`/`200` → referencia con costos; rechazo → `InventoryRejection`."""
        ...

    def reverse_output(self, operation_id: UUID, payload: dict[str, Any]) -> InventoryOperationRef: ...

    def find_by_key(self, company_id: UUID, operation_key: UUID) -> InventoryOperationRef | None:
        """`GET …/inventory-operations/by-key/{key}`; `404` → `None`."""
        ...

    def lookup_balances(
        self, company_id: UUID, branch_id: UUID, product_ids: Sequence[UUID]
    ) -> dict[UUID, BalanceInfo]:
        """`POST …/balances/lookup` (≤ 100); productos sin saldo con cantidad 0."""
        ...


# Fábrica del conjunto de dependencias ---------------------------------------


@dataclass(frozen=True, slots=True)
class PaymentMethodInfo:
    """Método global de pago (spec 020): referencia declarativa, no un pago registrado."""

    id: UUID
    code: str
    name: str
    status: str


class PaymentReferenceDirectory(Protocol):
    def get_payment_method(self, method_id: UUID) -> PaymentMethodInfo | None: ...


@dataclass(frozen=True, slots=True)
class Directories:
    operational_context: OperationalContextDirectory
    commercial: CommercialDirectory
    catalog: CatalogDirectory
    party: PartyDirectory
    payment_reference: PaymentReferenceDirectory
