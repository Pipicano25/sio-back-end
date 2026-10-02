"""Servicio de representantes legales (FR-070–FR-078, DS-06, DS-08, DS-13)."""

from __future__ import annotations

from datetime import datetime
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
    LegalRepresentativeRepository,
    OrganizationIdentityRepository,
    PersonIdentityRepository,
)
from party_identity_service.domain.contact import RelationState, normalize_optional_text
from party_identity_service.domain.legal_representative import (
    LegalRepresentative,
    RepresentativeType,
    is_primary_type,
    normalize_document_reference,
)


class LegalRepresentativeService:
    """Casos de uso de `organization_legal_representatives`."""

    def __init__(
        self,
        *,
        representatives: LegalRepresentativeRepository,
        organizations: OrganizationIdentityRepository,
        persons: PersonIdentityRepository,
    ) -> None:
        self.representatives = representatives
        self.organizations = organizations
        self.persons = persons

    def list_by_organization(
        self, organization_id: UUID, *, state: RelationState, page: int, page_size: int
    ) -> PageResult[LegalRepresentative]:
        self._organization(organization_id)
        return self.representatives.list_by_organization(
            organization_id, state=state, page=page, page_size=page_size
        )

    def get(self, representative_id: UUID) -> LegalRepresentative:
        representative = self.representatives.get_by_id(representative_id)
        if representative is None:
            raise NotFoundError("La relación de representación no existe.")
        return representative

    def register(
        self,
        organization_id: UUID,
        *,
        person_identity_id: UUID,
        representative_type: RepresentativeType,
        position: str | None,
        valid_from: datetime | None,
        source_document_reference: str | None,
        is_primary: bool | None,
        actor_id: str,
    ) -> LegalRepresentative:
        if is_primary is not None and is_primary != is_primary_type(representative_type):
            raise DomainValidationError(
                "is_primary",
                "is_primary se deriva del tipo: solo PRIMARY es principal.",
            )
        self._check_references(organization_id, person_identity_id)
        return self.representatives.create(
            organization_id=organization_id,
            person_identity_id=person_identity_id,
            representative_type=representative_type,
            position=normalize_optional_text(position),
            valid_from=valid_from,
            source_document_reference=normalize_document_reference(source_document_reference),
            actor_id=actor_id,
        )

    def set_primary(
        self,
        organization_id: UUID,
        *,
        person_identity_id: UUID,
        position: str | None,
        valid_from: datetime | None,
        source_document_reference: str | None,
        current_primary_version: int | None,
        actor_id: str,
    ) -> tuple[LegalRepresentative, bool]:
        """Establece el `PRIMARY`: crea el primero o sustituye el vigente (FR-074)."""
        self._check_references(organization_id, person_identity_id)
        return self.representatives.set_primary(
            organization_id,
            person_identity_id=person_identity_id,
            position=normalize_optional_text(position),
            valid_from=valid_from,
            source_document_reference=normalize_document_reference(source_document_reference),
            current_primary_version=current_primary_version,
            actor_id=actor_id,
        )

    def update(
        self,
        representative_id: UUID,
        *,
        expected_version: int,
        position: str | None,
        source_document_reference: str | None,
        actor_id: str,
        immutable_fields: list[str] | None = None,
    ) -> LegalRepresentative:
        if immutable_fields:
            raise ImmutableFieldError(
                "Persona, organización y tipo son inmutables (cerrar y crear): " + ", ".join(immutable_fields)
            )
        current = self.get(representative_id)
        if current.version != expected_version:
            raise VersionConflictError
        if not current.is_active:
            raise InvalidStatusTransitionError("La relación está cerrada y es inmutable.")

        values = {
            "position": normalize_optional_text(position),
            "source_document_reference": normalize_document_reference(source_document_reference),
        }
        if all(getattr(current, field) == value for field, value in values.items()):
            return current
        return self.representatives.update(
            representative_id, expected_version=expected_version, values=values, actor_id=actor_id
        )

    def close(self, representative_id: UUID, *, expected_version: int, actor_id: str) -> LegalRepresentative:
        """Cierra sin reactivación posible (DS-08)."""
        return self.representatives.close(representative_id, expected_version=expected_version, actor_id=actor_id)

    # -- interno --------------------------------------------------------------

    def _organization(self, organization_id: UUID):
        organization = self.organizations.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError("La organización solicitada no existe.")
        return organization

    def _check_references(self, organization_id: UUID, person_identity_id: UUID) -> None:
        organization = self._organization(organization_id)
        person = self.persons.get_by_id(person_identity_id)
        if person is None:
            raise PersonIdentityNotFoundError
        if organization.status != "ACTIVE":
            raise OrganizationIdentityInactiveError
        if person.status != "ACTIVE":
            raise PersonIdentityInactiveError
