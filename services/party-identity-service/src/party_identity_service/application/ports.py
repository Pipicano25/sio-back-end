"""Contratos usados por la capa de aplicación."""

from datetime import date
from typing import Protocol
from uuid import UUID

from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.person_identity import (
    PersonIdentificationType,
    PersonIdentity,
    PersonVerificationStatus,
)


class PersonIdentityRepository(Protocol):
    """Define operaciones de persistencia para identidades de personas."""

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        identification_country_id: UUID | None,
        identification_type: PersonIdentificationType | None,
        verification_status: PersonVerificationStatus | None,
    ) -> PageResult[PersonIdentity]:
        """Obtiene una página filtrada de identidades de persona.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros.
            search: Texto libre de búsqueda.
            identification_country_id: País externo exacto.
            identification_type: Tipo de identificación exacto.
            verification_status: Estado de verificación exacto.

        Returns:
            Página filtrada de identidades de persona.
        """
        ...

    def get_by_id(
        self,
        person_identity_id: UUID,
    ) -> PersonIdentity | None:
        """Obtiene una identidad de persona por identificador."""
        ...

    def create(
        self,
        *,
        identification_country_id: UUID,
        identification_type: PersonIdentificationType,
        identification_number: str,
        first_name: str,
        middle_name: str | None,
        last_name: str,
        second_last_name: str | None,
        birth_date: date | None,
        verification_status: PersonVerificationStatus,
        actor_id: str,
    ) -> PersonIdentity:
        """Crea una identidad global de persona."""
        ...

    def update(
        self,
        person_identity_id: UUID,
        *,
        expected_version: int,
        identification_country_id: UUID,
        identification_type: PersonIdentificationType,
        identification_number: str,
        first_name: str,
        middle_name: str | None,
        last_name: str,
        second_last_name: str | None,
        birth_date: date | None,
        verification_status: PersonVerificationStatus,
        actor_id: str,
    ) -> PersonIdentity | None:
        """Actualiza completamente una identidad global de persona."""
        ...
