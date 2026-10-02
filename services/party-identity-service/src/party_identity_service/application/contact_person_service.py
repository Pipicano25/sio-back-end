"""Servicio de personas de contacto de una organización (FR-040–FR-047, DS-05, DS-07)."""

from __future__ import annotations

from uuid import UUID

from party_identity_service.application.exceptions import (
    DomainValidationError,
    ImmutableFieldError,
    InvalidStatusTransitionError,
    NotFoundError,
    OrganizationIdentityInactiveError,
    PersonIdentityInactiveError,
    PersonIdentityNotFoundError,
    VersionConflictError,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.application.ports import (
    ContactPersonRepository,
    OrganizationIdentityRepository,
    PersonIdentityRepository,
)
from party_identity_service.domain.contact import (
    ContactPerson,
    normalize_email,
    normalize_optional_text,
)


class ContactPersonService:
    """Casos de uso de `organization_contact_persons`."""

    def __init__(
        self,
        *,
        contacts: ContactPersonRepository,
        organizations: OrganizationIdentityRepository,
        persons: PersonIdentityRepository,
    ) -> None:
        self.contacts = contacts
        self.organizations = organizations
        self.persons = persons

    def list_by_organization(
        self, organization_id: UUID, *, is_active: bool, page: int, page_size: int
    ) -> PageResult[ContactPerson]:
        self._organization(organization_id)
        return self.contacts.list_by_organization(
            organization_id, is_active=is_active, page=page, page_size=page_size
        )

    def get(self, contact_id: UUID) -> ContactPerson:
        contact = self.contacts.get_by_id(contact_id)
        if contact is None:
            raise NotFoundError("La persona de contacto no existe.")
        return contact

    def create(
        self,
        organization_id: UUID,
        *,
        person_identity_id: UUID | None,
        position: str | None,
        email: str | None,
        phone: str | None,
        is_primary: bool,
        actor_id: str,
    ) -> ContactPerson:
        position, email, phone = self._normalize(position, email, phone, person_identity_id)
        organization = self._organization(organization_id)
        if organization.status != "ACTIVE":
            raise OrganizationIdentityInactiveError
        self._check_person(person_identity_id)

        return self.contacts.create(
            organization_id=organization_id,
            person_identity_id=person_identity_id,
            position=position,
            email=email,
            phone=phone,
            is_primary=is_primary,
            actor_id=actor_id,
        )

    def update(
        self,
        contact_id: UUID,
        *,
        expected_version: int,
        person_identity_id: UUID | None,
        position: str | None,
        email: str | None,
        phone: str | None,
        actor_id: str,
        immutable_fields: list[str] | None = None,
    ) -> ContactPerson:
        if immutable_fields:
            raise ImmutableFieldError(
                "is_primary solo cambia con set-primary y la organización es inmutable: "
                + ", ".join(immutable_fields)
            )
        current = self.get(contact_id)
        if current.version != expected_version:
            raise VersionConflictError
        if not current.is_active:
            raise InvalidStatusTransitionError("La persona de contacto está inactiva.")
        position, email, phone = self._normalize(position, email, phone, person_identity_id)

        values = {
            "person_identity_id": person_identity_id,
            "position": position,
            "email": email,
            "phone": phone,
        }
        if all(getattr(current, field) == value for field, value in values.items()):
            return current

        if person_identity_id != current.person_identity_id:
            self._check_person(person_identity_id)

        return self.contacts.update(
            contact_id, expected_version=expected_version, values=values, actor_id=actor_id
        )

    def deactivate(self, contact_id: UUID, *, expected_version: int, actor_id: str) -> ContactPerson:
        current = self.get(contact_id)
        if current.version != expected_version:
            raise VersionConflictError
        if not current.is_active:
            raise InvalidStatusTransitionError("La persona de contacto ya está inactiva.")
        return self.contacts.set_active(
            contact_id, expected_version=expected_version, active=False, actor_id=actor_id
        )

    def reactivate(self, contact_id: UUID, *, expected_version: int, actor_id: str) -> ContactPerson:
        current = self.get(contact_id)
        if current.version != expected_version:
            raise VersionConflictError
        if current.is_active:
            raise InvalidStatusTransitionError("La persona de contacto ya está activa.")
        if self._organization(current.organization_identity_id).status != "ACTIVE":
            raise OrganizationIdentityInactiveError
        return self.contacts.set_active(
            contact_id, expected_version=expected_version, active=True, actor_id=actor_id
        )

    def set_primary(self, contact_id: UUID, *, expected_version: int, actor_id: str) -> ContactPerson:
        """Establece el contacto principal de forma atómica (DS-05, FR-044a)."""
        return self.contacts.set_primary(contact_id, expected_version=expected_version, actor_id=actor_id)

    # -- interno --------------------------------------------------------------

    @staticmethod
    def _normalize(position, email, phone, person_identity_id):
        position = normalize_optional_text(position)
        email = normalize_email(email)
        phone = normalize_optional_text(phone)
        if email is None and phone is None and person_identity_id is None:
            raise DomainValidationError(
                "email",
                "Informe al menos uno de correo, teléfono o persona vinculada.",
            )
        return position, email, phone

    def _organization(self, organization_id: UUID):
        organization = self.organizations.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError("La organización solicitada no existe.")
        return organization

    def _check_person(self, person_identity_id: UUID | None) -> None:
        if person_identity_id is None:
            return
        person = self.persons.get_by_id(person_identity_id)
        if person is None:
            raise PersonIdentityNotFoundError
        if person.status != "ACTIVE":
            raise PersonIdentityInactiveError
