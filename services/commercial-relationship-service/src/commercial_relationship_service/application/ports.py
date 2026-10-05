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
    """Empresa por UUID en Operational Context (autorreferencia, FR-028)."""

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
    """Party Identity con el token del usuario (R-06)."""

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
