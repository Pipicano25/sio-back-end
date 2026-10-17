"""Puertos de las dependencias externas (Principio XV; `contracts/dependencies.md`).

Cada puerto tiene un único adaptador HTTP real en `infrastructure/`; las pruebas
inyectan dobles por DI. Un `get_*` devuelve `None` ante `404` del proveedor; la
indisponibilidad se expresa con `DependencyUnavailableError`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
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


@dataclass(frozen=True, slots=True)
class SupplierInfo:
    id: UUID
    company_id: UUID
    organization_identity_id: UUID
    display_name: str
    status: str


@dataclass(frozen=True, slots=True)
class PaymentConditionInfo:
    id: UUID
    company_id: UUID
    company_supplier_id: UUID
    payment_condition_type_id: UUID
    currency_code: str
    payment_terms_days: int
    valid_from: date | None
    valid_to: date | None
    status: str


@dataclass(frozen=True, slots=True)
class CompanyProductInfo:
    id: UUID
    company_id: UUID
    global_product_id: UUID
    internal_code: str
    display_name: str
    is_purchasable: bool
    inventory_control_enabled: bool
    status: str
    purchase_tax_percentage: Decimal | None = None
    """Spec 021 (FR-021-08): tasa predeterminada de impuesto de compra; `None` = sin configurar."""


@dataclass(frozen=True, slots=True)
class CompanyPresentationInfo:
    id: UUID
    company_id: UUID
    company_product_id: UUID
    global_product_presentation_id: UUID
    is_purchasable: bool
    status: str


@dataclass(frozen=True, slots=True)
class SupplierProductInfo:
    id: UUID
    company_id: UUID
    company_supplier_id: UUID
    company_product_id: UUID
    company_product_presentation_id: UUID | None
    expected_supplier_lead_time_hours: Decimal | None
    status: str


class CommercialDirectory(Protocol):
    def get_supplier(self, supplier_id: UUID) -> SupplierInfo | None: ...

    def get_payment_condition(self, condition_id: UUID) -> PaymentConditionInfo | None: ...

    def lookup_products(self, ids: Sequence[UUID]) -> dict[UUID, CompanyProductInfo]:
        """Productos encontrados (≤ 100 ids distintos); los no encontrados no aparecen."""
        ...

    def lookup_presentations(self, ids: Sequence[UUID]) -> dict[UUID, CompanyPresentationInfo]: ...

    def lookup_pricing_coverage(self, company_id: UUID, currency_code: str, ids: Sequence[UUID]) -> dict[UUID, bool]:
        """Spec 021 (FR-021-35): `True` si la presentación tiene política de ganancia aplicable en una lista activa,
        vigente y de la moneda; `False` si no la tiene o no es de la empresa. Un fallo técnico es `503`."""
        ...

    def get_supplier_product(self, supplier_product_id: UUID) -> SupplierProductInfo | None: ...


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
    def lookup_presentations(self, ids: Sequence[UUID]) -> dict[UUID, GlobalPresentationInfo]: ...

    def get_product(self, product_id: UUID) -> GlobalProductInfo | None: ...

    def get_unit(self, unit_id: UUID) -> UnitInfo | None: ...


# Party Identity y Payment Reference ----------------------------------------


@dataclass(frozen=True, slots=True)
class OrganizationInfo:
    """Identidad de organización; la identificación puede faltar en una organización existente (D-08)."""

    id: UUID
    identification_type: str | None
    identification_number: str | None


class PartyDirectory(Protocol):
    def get_organization(self, organization_id: UUID) -> OrganizationInfo | None: ...


@dataclass(frozen=True, slots=True)
class PaymentConditionTypeInfo:
    id: UUID
    code: str
    status: str


@dataclass(frozen=True, slots=True)
class PaymentMethodInfo:
    """Método global de pago (spec 020): referencia declarativa, no un pago registrado."""

    id: UUID
    code: str
    name: str
    status: str


class PaymentReferenceDirectory(Protocol):
    def get_condition_type(self, type_id: UUID) -> PaymentConditionTypeInfo | None: ...

    def get_payment_method(self, method_id: UUID) -> PaymentMethodInfo | None: ...


# Inventory -----------------------------------------------------------------


class InventoryRejection(Exception):
    """Rechazo definitivo de Inventory (`404`, `409` o `422`): no se reintenta sin cambios."""

    def __init__(self, status: int, code: str | None, body: dict[str, Any] | None = None) -> None:
        super().__init__(code or str(status))
        self.status = status
        self.code = code
        self.body = body or {}


@dataclass(frozen=True, slots=True)
class InventoryOperationRef:
    """Operación aplicada en Inventory: solo se guarda su `id` (FR-046)."""

    id: UUID
    operation_type: str | None = None
    reverses_operation_id: UUID | None = None


class InventoryGateway(Protocol):
    def apply_entry(self, payload: dict[str, Any]) -> InventoryOperationRef:
        """`POST /inventory-entries`; `201`/`200` → referencia; rechazo → `InventoryRejection`."""
        ...

    def reverse_entry(self, operation_id: UUID, payload: dict[str, Any]) -> InventoryOperationRef: ...

    def find_by_key(self, company_id: UUID, operation_key: UUID) -> InventoryOperationRef | None:
        """`GET …/inventory-operations/by-key/{key}`; `404` → `None`."""
        ...


# Fábrica del conjunto de dependencias ---------------------------------------


@dataclass(frozen=True, slots=True)
class Directories:
    operational_context: OperationalContextDirectory
    commercial: CommercialDirectory
    catalog: CatalogDirectory
    party: PartyDirectory
    payment_reference: PaymentReferenceDirectory


# ---------------------------------------------------------------- spec 021: entrega a Commercial Relationship


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Resultado de entregar una solicitud de precio (EXC-001).

    `outcome`: `ACCEPTED` (CR la guardó, `202`), `REJECTED` (`409`: defecto, no se reintenta solo) o `RETRY`
    (caída, tiempo agotado, `5xx`, `401`/`403` u otro estado: se reintenta con espera creciente).
    """

    outcome: str
    code: str | None = None


class CommercialPricingGateway(Protocol):
    def submit(self, company_id: UUID, payload: dict[str, Any]) -> DeliveryResult: ...
