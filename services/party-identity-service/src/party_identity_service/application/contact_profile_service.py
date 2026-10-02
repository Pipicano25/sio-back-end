"""Servicio de perfiles de contacto versionados (FR-010–FR-031, DS-01–DS-04, R-03, R-04).

Orden de una versión nueva (contracts/rest-api.md §1): identidad existe y
`ACTIVE` → versión esperada → no-op semántico → geografía (solo si cambió) →
membresía en Operational Context → escritura bajo bloqueo con revalidación de
la versión. Las llamadas externas se hacen antes del bloqueo.
"""

from __future__ import annotations

import logging
from typing import Literal, Protocol
from uuid import UUID

from party_identity_service.application.exceptions import (
    ContactProfileNotFoundError,
    DomainValidationError,
    NotFoundError,
    OrganizationIdentityInactiveError,
    PersonIdentityInactiveError,
    VersionConflictError,
)
from party_identity_service.application.geography_validation import validate_profile_geography
from party_identity_service.application.pagination import PageResult
from party_identity_service.application.ports import (
    ContactProfileRepository,
    LocationDirectory,
    MembershipResolver,
)
from party_identity_service.domain.contact import ContactData, ContactProfile
from party_identity_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

Kind = Literal["person", "organization"]


class OwnerLookup(Protocol):
    """Lectura de la identidad propietaria (persona u organización)."""

    def get_by_id(self, owner_id: UUID): ...


class ContactProfileService:
    """Casos de uso de los perfiles de contacto de un tipo de parte."""

    def __init__(
        self,
        *,
        kind: Kind,
        profiles: ContactProfileRepository,
        owners: OwnerLookup,
        locations: LocationDirectory,
        memberships: MembershipResolver,
    ) -> None:
        self.kind = kind
        self.profiles = profiles
        self.owners = owners
        self.locations = locations
        self.memberships = memberships

    # -- consultas --------------------------------------------------------------

    def get_active(self, owner_id: UUID) -> ContactProfile:
        self._require_owner(owner_id)
        current = self.profiles.get_active(owner_id)
        if current is None:
            raise ContactProfileNotFoundError
        return current

    def list_versions(self, owner_id: UUID, *, page: int, page_size: int) -> PageResult[ContactProfile]:
        self._require_owner(owner_id)
        return self.profiles.list_versions(owner_id, page=page, page_size=page_size)

    def get_version(self, profile_id: UUID) -> ContactProfile:
        profile = self.profiles.get_version(profile_id)
        if profile is None:
            raise NotFoundError("La versión de perfil solicitada no existe.")
        return profile

    # -- escrituras -------------------------------------------------------------

    def register(
        self,
        owner_id: UUID,
        *,
        email: str | None,
        phone: str | None,
        address_line: str | None,
        country_id: UUID | None,
        administrative_division_id: UUID | None,
        city_id: UUID | None,
        postal_code: str | None,
        confirmed_by_company_id: UUID,
        expected_version: int | None,
        actor_id: str,
        keycloak_user_id: str,
    ) -> tuple[ContactProfile, bool]:
        """Registra una versión nueva del perfil.

        Returns:
            La versión vigente resultante y `True` si se creó una versión nueva
            (`False` en una solicitud semánticamente idéntica).
        """
        data = ContactData.normalized(
            email=email,
            phone=phone,
            address_line=address_line,
            country_id=country_id,
            administrative_division_id=administrative_division_id,
            city_id=city_id,
            postal_code=postal_code,
        )
        if not data.has_contact:
            raise DomainValidationError(
                "email",
                "Informe al menos uno de correo, teléfono o dirección.",
            )

        owner = self._require_owner(owner_id)
        if owner.status != "ACTIVE":
            raise (
                PersonIdentityInactiveError
                if self.kind == "person"
                else OrganizationIdentityInactiveError
            )

        current = self.profiles.get_active(owner_id)
        if current is not None:
            # Sin versión, el cliente cree que no hay vigente: su vista está
            # desactualizada (también si otra solicitud acaba de crearla) → 409.
            if expected_version is None or expected_version != current.version:
                raise VersionConflictError
            if current.data == data and current.confirmed_by_company_id == confirmed_by_company_id:
                # No-op semántico (DS-04): sin escritura ni dependencias.
                return current, False

        validate_profile_geography(
            self.locations,
            new=data.geography,
            current=current.data.geography if current is not None else None,
        )
        confirmed_by_user_id = self.memberships.resolve(
            company_id=confirmed_by_company_id,
            keycloak_user_id=keycloak_user_id,
        )

        profile = self.profiles.replace(
            owner_id,
            expected_active_id=current.id if current is not None else None,
            expected_version=current.version if current is not None else None,
            data=data,
            confirmed_by_company_id=confirmed_by_company_id,
            confirmed_by_user_id=confirmed_by_user_id,
            actor_id=actor_id,
        )
        logger.info(
            "Perfil de contacto registrado tipo=%s propietario=%s version_id=%s",
            self.kind,
            owner_id,
            profile.id,
        )
        return profile, True

    def close(self, owner_id: UUID, *, expected_version: int, actor_id: str) -> ContactProfile:
        """Cierra la versión vigente sin reemplazo (DS-03, FR-020)."""
        self._require_owner(owner_id)
        profile = self.profiles.close(owner_id, expected_version=expected_version, actor_id=actor_id)
        logger.info(
            "Perfil de contacto cerrado tipo=%s propietario=%s version_id=%s",
            self.kind,
            owner_id,
            profile.id,
        )
        return profile

    def _require_owner(self, owner_id: UUID):
        owner = self.owners.get_by_id(owner_id)
        if owner is None:
            raise NotFoundError(
                "La persona solicitada no existe."
                if self.kind == "person"
                else "La organización solicitada no existe."
            )
        return owner
