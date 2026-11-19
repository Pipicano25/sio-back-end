"""Puertos de integración de Commercial Relationship Service (Principio XV).

Cada proveedor tiene un único puerto con su adaptador HTTP real en
`infrastructure/`; las pruebas inyectan dobles en `create_app` (FR-050). Los
adaptadores traducen la respuesta del proveedor a estos valores o a las
excepciones de `application/exceptions.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CompanyAccess:
    """Resultado de la vía propia de `operational-access` (R-02).

    Attributes:
        member_active: El usuario tiene membresía `ACTIVE` en la empresa.
        company_active: La empresa está `ACTIVE`; `None` si no es miembro (no se revela).
    """

    member_active: bool
    company_active: bool | None


@dataclass(frozen=True, slots=True)
class MemberCompany:
    """Empresa con membresía `ACTIVE` del usuario según `me/operational-context` (FR-046)."""

    company_id: UUID
    company_status: str


@dataclass(frozen=True, slots=True)
class GlobalProductRef:
    """Elegibilidad de un producto global según `batch-lookup` (R-04)."""

    found: bool
    status: str | None = None
    eligible_for_adoption: bool | None = None


@dataclass(frozen=True, slots=True)
class GlobalPresentationRef:
    """Presentación global según `presentations/batch-lookup` (R-07)."""

    found: bool
    global_product_id: UUID | None = None
    status: str | None = None
    eligible_for_adoption: bool | None = None


@dataclass(frozen=True, slots=True)
class PaymentConditionTypeRef:
    """Tipo de condición de pago de Payment Reference (R-08).

    `code` se usa solo en memoria para FR-033; nunca se guarda (Principio III).
    """

    id: UUID
    code: str
    status: str


@dataclass(frozen=True, slots=True)
class IdentityRef:
    """Persona u organización de Party Identity: solo su estado (FR-057)."""

    id: UUID
    status: str


@dataclass(frozen=True, slots=True)
class ContactPersonRef:
    """Persona de contacto de Party Identity: organización y si está activa."""

    id: UUID
    organization_identity_id: UUID
    is_active: bool


class CompanyAccessDirectory(Protocol):
    """Acceso del usuario a una empresa en Operational Context (vía propia)."""

    def check_company_access(self, company_id: UUID) -> CompanyAccess:
        """Raises `OperationalAccessDeniedError` (403) o `DependencyUnavailableError`."""
        ...

    def list_member_companies(self) -> list[MemberCompany]:
        """Empresas con membresía `ACTIVE` del usuario (resumen, FR-046).

        Raises `OperationalAccessDeniedError` (403) o `DependencyUnavailableError`.
        """
        ...


class CompanyDirectory(Protocol):
    """Empresa por UUID en Operational Context (autorreferencia, FR-028).

    Opcional (spec 025, T060): `find_company_organizations(company_ids) -> dict[UUID, UUID | None]`, el mismo
    resultado que `find_company_organization` por empresa; el resumen lo usa si el adaptador lo tiene.
    """

    def get_company_organization(self, company_id: UUID) -> UUID:
        """Raises `NotFoundError`, `OperationalAccessDeniedError` o `DependencyUnavailableError`."""
        ...

    def find_company_organization(self, company_id: UUID) -> UUID | None:
        """Para presentación (resumen, FR-046): `None` ante `404` o `403`.

        Raises `DependencyUnavailableError`.
        """
        ...


class ProductCatalogDirectory(Protocol):
    """Product Catalog con la identidad técnica propia (R-04, R-05)."""

    def lookup_product(self, global_product_id: UUID) -> GlobalProductRef:
        """Raises `DependencyUnavailableError`."""
        ...

    def register_first_use(
        self,
        global_product_id: UUID,
        global_product_presentation_id: UUID | None = None,
    ) -> None:
        """Primer uso del producto o, si se indica, de la presentación (R-07).

        Raises `GlobalProductNotFoundError`, `GlobalProductNotEligibleError` (sin
        presentación), `GlobalPresentationNotFoundError`,
        `GlobalPresentationNotEligibleError`, `GlobalPresentationOfOtherProductError`
        (con presentación) o `DependencyUnavailableError`.
        """
        ...

    def lookup_presentation(self, global_product_presentation_id: UUID) -> GlobalPresentationRef:
        """Elegibilidad de una presentación global. Raises `DependencyUnavailableError`."""
        ...

    def get_product_base_unit(self, global_product_id: UUID) -> UUID | None:
        """`base_unit_id` del producto global; `None` si no existe (FR-022).

        Raises `DependencyUnavailableError`.
        """
        ...


class PaymentReferenceDirectory(Protocol):
    """Payment Reference con la identidad técnica propia (R-08, DS-02)."""

    def get_condition_type(self, condition_type_id: UUID) -> PaymentConditionTypeRef | None:
        """`None` si no existe. Raises `DependencyUnavailableError`."""
        ...


class PartyDirectory(Protocol):
    """Party Identity con el token del usuario (R-06).

    Opcional (spec 025, T060): `find_organization_names(ids) -> dict[UUID, str | None]`, el mismo resultado que
    `find_organization_name` por organización; el resumen lo usa si el adaptador lo tiene.
    """

    def get_person(self, person_identity_id: UUID) -> IdentityRef | None:
        """`None` si no existe. Raises `PartyIdentityAccessDeniedError` o
        `DependencyUnavailableError`."""
        ...

    def get_organization(self, organization_identity_id: UUID) -> IdentityRef | None:
        """Ídem para organizaciones."""
        ...

    def get_contact_person(self, contact_person_id: UUID) -> ContactPersonRef | None:
        """Ídem para personas de contacto."""
        ...

    def find_organization_name(self, organization_identity_id: UUID) -> str | None:
        """Razón social para presentación (resumen, FR-046): `None` ante `404` o `403`.

        Raises `DependencyUnavailableError`.
        """
        ...


# --------------------------------------------------------------------------
# Spec 027: adopción masiva (research R4)
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CatalogMatchPage:
    """Página de `products/match` (modo conductor): ids en orden, última posición y si hay más."""

    ids: list[UUID]
    after: dict | None
    has_more: bool


@dataclass(frozen=True, slots=True)
class CatalogIdentifier:
    """Identificador `ACTIVE` de un producto global según `products/summaries/batch-lookup`."""

    type: str
    value: str
    is_primary: bool
    global_product_presentation_id: UUID | None


@dataclass(frozen=True, slots=True)
class CatalogProductSummary:
    """Resumen de un producto global: nombre canónico, estado e identificadores `ACTIVE`."""

    id: UUID
    found: bool
    canonical_name: str | None = None
    status: str | None = None
    identifiers: tuple[CatalogIdentifier, ...] = ()


@dataclass(frozen=True, slots=True)
class CatalogPresentation:
    """Presentación global de un producto según `GET products/{id}/presentations`."""

    id: UUID
    global_product_id: UUID
    status: str
    is_base: bool
    eligible_for_adoption: bool


@dataclass(frozen=True, slots=True)
class CatalogProductLookup:
    """Elegibilidad de un producto global (`products/batch-lookup`) con su id."""

    id: UUID
    ref: GlobalProductRef


@dataclass(frozen=True, slots=True)
class CatalogPresentationLookup:
    """Elegibilidad de una presentación global (`presentations/batch-lookup`) con su id."""

    id: UUID
    ref: GlobalPresentationRef


class ProductCatalogBulkDirectory(Protocol):
    """Lecturas por lotes de Product Catalog para la adopción masiva (spec 027, R4).

    Usa la identidad técnica propia, como `ProductCatalogDirectory`. Cada lote admite hasta 100 ids. Ante un
    fallo de red, tiempo agotado o una respuesta inesperada, todos los métodos lanzan
    `DependencyUnavailableError` (la misma excepción del puerto individual; ver la nota de T005 en `tasks.md`).
    """

    def match_products(
        self,
        *,
        category_ids: list[UUID],
        brand_ids: list[UUID],
        include_descendants: bool,
        after: dict | None,
        limit: int,
    ) -> CatalogMatchPage:
        """Productos globales `ACTIVE` que cumplen el filtro, después de `after` (Historia 3)."""
        ...

    def lookup_products(self, ids: list[UUID]) -> list[CatalogProductLookup]:
        """Elegibilidad de hasta 100 productos globales, en el orden recibido."""
        ...

    def product_summaries(self, ids: list[UUID]) -> dict[UUID, CatalogProductSummary]:
        """Nombre canónico e identificadores de hasta 100 productos globales."""
        ...

    def product_presentations(self, global_product_id: UUID) -> list[CatalogPresentation]:
        """Presentaciones `ACTIVE` del producto global, con `is_base`; vacío si el producto no existe."""
        ...

    def lookup_presentations(self, ids: list[UUID]) -> list[CatalogPresentationLookup]:
        """Elegibilidad de hasta 100 presentaciones globales, en el orden recibido."""
        ...
