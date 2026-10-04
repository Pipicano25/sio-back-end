"""Validación de referencias externas compartida por clientes y proveedores (R-06, R-07).

Nunca se guarda una referencia sin validarla en su proveedor (RN-12); los
rechazos se expresan con los códigos de `contracts/errors.md`.
"""

from __future__ import annotations

from uuid import UUID

from commercial_relationship_service.application.exceptions import (
    ContactPersonInvalidError,
    OrganizationIdentityInactiveError,
    OrganizationIdentityNotFoundError,
    PersonIdentityInactiveError,
    PersonIdentityNotFoundError,
    SelfRelationshipNotAllowedError,
)
from commercial_relationship_service.application.ports import CompanyDirectory, PartyDirectory


def require_active_person(party: PartyDirectory, person_identity_id: UUID) -> None:
    """La persona existe y está `ACTIVE` (FR-021)."""
    person = party.get_person(person_identity_id)

    if person is None:
        raise PersonIdentityNotFoundError(field="person_identity_id")

    if person.status != "ACTIVE":
        raise PersonIdentityInactiveError(field="person_identity_id")


def require_active_organization(party: PartyDirectory, organization_identity_id: UUID) -> None:
    """La organización existe y está `ACTIVE` (FR-021, FR-031)."""
    organization = party.get_organization(organization_identity_id)

    if organization is None:
        raise OrganizationIdentityNotFoundError(field="organization_identity_id")

    if organization.status != "ACTIVE":
        raise OrganizationIdentityInactiveError(field="organization_identity_id")


def require_valid_contact(
    party: PartyDirectory,
    contact_person_id: UUID,
    organization_identity_id: UUID,
) -> None:
    """El contacto existe, pertenece a la misma organización y está activo (FR-022, RN-07)."""
    contact = party.get_contact_person(contact_person_id)

    if (
        contact is None
        or contact.organization_identity_id != organization_identity_id
        or not contact.is_active
    ):
        raise ContactPersonInvalidError(field="preferred_contact_person_id")


def reject_self_relationship(
    companies: CompanyDirectory,
    company_id: UUID,
    organization_identity_id: UUID,
) -> None:
    """La organización no es la de la propia empresa (FR-028, DS-15). No se guarda nada."""
    if companies.get_company_organization(company_id) == organization_identity_id:
        raise SelfRelationshipNotAllowedError(field="organization_identity_id")
