"""Dobles de los puertos de integración (solo pruebas, Principio IV, FR-050).

Se inyectan en `create_app` mediante fábricas; el código de producción solo
tiene los adaptadores HTTP. Cada doble registra sus llamadas para que las
pruebas verifiquen el orden y la ausencia de llamadas (FR-011, R-02).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import jwt

from commercial_relationship_service.application.exceptions import (
    OPERATIONAL_CONTEXT,
    PARTY_IDENTITY,
    PRODUCT_CATALOG,
    DependencyUnavailableError,
    GlobalProductNotEligibleError,
    GlobalProductNotFoundError,
    NotFoundError,
    OperationalAccessDeniedError,
    PartyIdentityAccessDeniedError,
)
from commercial_relationship_service.application.ports import (
    CompanyAccess,
    ContactPersonRef,
    GlobalProductRef,
    IdentityRef,
    MemberCompany,
)


def subject_of(authorization: str | None) -> str | None:
    """`sub` del token de la solicitud (sin verificar: lo verificó `sio-auth`)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    claims = jwt.decode(authorization.split(" ", 1)[1], options={"verify_signature": False})
    return claims.get("sub")


def _unavailable(provider: str, operation: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(provider=provider, cause="FAKE_UNAVAILABLE", operation=operation)


# --------------------------------------------------------------------------
# Operational Context
# --------------------------------------------------------------------------


@dataclass
class FakeOperationalContext:
    """Membresías por `sub` y empresa; empresas inactivas; organización de cada empresa."""

    members: set[tuple[str, UUID]] = field(default_factory=set)
    inactive_members: set[tuple[str, UUID]] = field(default_factory=set)
    inactive_companies: set[UUID] = field(default_factory=set)
    organizations: dict[UUID, UUID] = field(default_factory=dict)
    access_forbidden: bool = False
    access_unavailable: bool = False
    company_forbidden: bool = False
    company_unavailable: bool = False
    access_calls: list[tuple[str | None, UUID]] = field(default_factory=list)
    company_calls: list[UUID] = field(default_factory=list)
    me_calls: list[str | None] = field(default_factory=list)

    def add_member(self, sub: str, company_id: UUID) -> None:
        self.members.add((sub, company_id))
        self.inactive_members.discard((sub, company_id))

    def deactivate_member(self, sub: str, company_id: UUID) -> None:
        self.members.discard((sub, company_id))
        self.inactive_members.add((sub, company_id))

    def access_for(self, request) -> FakeCompanyAccessDirectory:
        return FakeCompanyAccessDirectory(self, subject_of(request.headers.get("authorization")))

    def companies_for(self, request) -> FakeCompanyDirectory:
        return FakeCompanyDirectory(self)


class FakeCompanyAccessDirectory:
    def __init__(self, state: FakeOperationalContext, sub: str | None) -> None:
        self._state = state
        self._sub = sub

    def check_company_access(self, company_id: UUID) -> CompanyAccess:
        self._state.access_calls.append((self._sub, company_id))

        if self._state.access_forbidden:
            raise OperationalAccessDeniedError()

        if self._state.access_unavailable:
            raise _unavailable(OPERATIONAL_CONTEXT, "operational_access")

        if (self._sub, company_id) not in self._state.members:
            return CompanyAccess(member_active=False, company_active=None)

        return CompanyAccess(
            member_active=True,
            company_active=company_id not in self._state.inactive_companies,
        )

    def list_member_companies(self) -> list[MemberCompany]:
        self._state.me_calls.append(self._sub)

        if self._state.access_forbidden:
            raise OperationalAccessDeniedError()

        if self._state.access_unavailable:
            raise _unavailable(OPERATIONAL_CONTEXT, "me_operational_context")

        companies = sorted(
            (company for sub, company in self._state.members if sub == self._sub), key=str
        )
        return [
            MemberCompany(
                company_id=company,
                company_status="INACTIVE" if company in self._state.inactive_companies else "ACTIVE",
            )
            for company in companies
        ]


class FakeCompanyDirectory:
    def __init__(self, state: FakeOperationalContext) -> None:
        self._state = state

    def get_company_organization(self, company_id: UUID) -> UUID:
        self._state.company_calls.append(company_id)

        if self._state.company_forbidden:
            raise OperationalAccessDeniedError()

        if self._state.company_unavailable:
            raise _unavailable(OPERATIONAL_CONTEXT, "get_company")

        if company_id not in self._state.organizations:
            raise NotFoundError

        return self._state.organizations[company_id]

    def find_company_organization(self, company_id: UUID) -> UUID | None:
        self._state.company_calls.append(company_id)

        if self._state.company_unavailable:
            raise _unavailable(OPERATIONAL_CONTEXT, "get_company_for_summary")

        if self._state.company_forbidden:
            return None

        return self._state.organizations.get(company_id)


# --------------------------------------------------------------------------
# Product Catalog
# --------------------------------------------------------------------------


@dataclass
class FakeProductCatalog:
    """Productos globales por UUID y registro de primer uso."""

    products: dict[UUID, GlobalProductRef] = field(default_factory=dict)
    lookup_unavailable: bool = False
    first_use_error: str | None = None  # "not_found" | "not_eligible" | "unavailable"
    lookup_calls: list[UUID] = field(default_factory=list)
    first_use_calls: list[UUID] = field(default_factory=list)

    def add(self, product_id: UUID, *, status: str = "ACTIVE", eligible: bool = True) -> UUID:
        self.products[product_id] = GlobalProductRef(
            found=True, status=status, eligible_for_adoption=eligible
        )
        return product_id

    def lookup_product(self, global_product_id: UUID) -> GlobalProductRef:
        self.lookup_calls.append(global_product_id)

        if self.lookup_unavailable:
            raise _unavailable(PRODUCT_CATALOG, "products_batch_lookup")

        return self.products.get(global_product_id, GlobalProductRef(found=False))

    def register_first_use(self, global_product_id: UUID) -> None:
        self.first_use_calls.append(global_product_id)

        if self.first_use_error == "not_found":
            raise GlobalProductNotFoundError(field="global_product_id")

        if self.first_use_error == "not_eligible":
            raise GlobalProductNotEligibleError(field="global_product_id")

        if self.first_use_error == "unavailable":
            raise _unavailable(PRODUCT_CATALOG, "products_first_use")


# --------------------------------------------------------------------------
# Party Identity
# --------------------------------------------------------------------------


@dataclass
class FakePartyIdentity:
    """Personas, organizaciones y personas de contacto por UUID."""

    persons: dict[UUID, str] = field(default_factory=dict)
    organizations: dict[UUID, str] = field(default_factory=dict)
    contacts: dict[UUID, ContactPersonRef] = field(default_factory=dict)
    names: dict[UUID, str] = field(default_factory=dict)
    forbidden: bool = False
    unavailable: bool = False
    calls: list[tuple[str, UUID]] = field(default_factory=list)

    def add_contact(self, contact_id: UUID, organization_id: UUID, *, is_active: bool = True) -> UUID:
        self.contacts[contact_id] = ContactPersonRef(
            id=contact_id, organization_identity_id=organization_id, is_active=is_active
        )
        return contact_id

    def _guard(self, operation: str, identity_id: UUID) -> None:
        self.calls.append((operation, identity_id))

        if self.forbidden:
            raise PartyIdentityAccessDeniedError()

        if self.unavailable:
            raise _unavailable(PARTY_IDENTITY, operation)

    def get_person(self, person_identity_id: UUID) -> IdentityRef | None:
        self._guard("get_person", person_identity_id)
        status = self.persons.get(person_identity_id)
        return None if status is None else IdentityRef(id=person_identity_id, status=status)

    def get_organization(self, organization_identity_id: UUID) -> IdentityRef | None:
        self._guard("get_organization", organization_identity_id)
        status = self.organizations.get(organization_identity_id)
        return None if status is None else IdentityRef(id=organization_identity_id, status=status)

    def get_contact_person(self, contact_person_id: UUID) -> ContactPersonRef | None:
        self._guard("get_contact_person", contact_person_id)
        return self.contacts.get(contact_person_id)

    def find_organization_name(self, organization_identity_id: UUID) -> str | None:
        self.calls.append(("get_organization_name", organization_identity_id))

        if self.unavailable:
            raise _unavailable(PARTY_IDENTITY, "get_organization_name")

        if self.forbidden:
            return None

        return self.names.get(organization_identity_id)
