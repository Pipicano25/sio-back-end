"""Casos de uso para identidades globales de personas."""

from datetime import date
from uuid import UUID

from party_identity_service.application.exceptions import (
    InvalidIdentificationNumberError,
    PersonIdentityNotFoundError,
)
from party_identity_service.application.identification_rules import (
    IdentificationRuleSet,
    normalize_identification_number,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.application.ports import PersonIdentityRepository
from party_identity_service.domain.person_identity import (
    PersonIdentificationType,
    PersonIdentity,
    PersonVerificationStatus,
)


class PersonIdentityService:
    """Orquesta casos de uso de identidades de personas."""

    def __init__(
        self,
        repository: PersonIdentityRepository,
        identification_rules: IdentificationRuleSet,
    ) -> None:
        """Inicializa el servicio de aplicación.

        Args:
            repository: Puerto de persistencia de identidades de persona.
            identification_rules: Reglas de identificación configuradas.
        """
        self.repository = repository
        self.identification_rules = identification_rules

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        identification_country_id: UUID | None = None,
        identification_type: PersonIdentificationType | None = None,
        verification_status: PersonVerificationStatus | None = None,
    ) -> PageResult[PersonIdentity]:
        """Obtiene identidades de persona con paginación y filtros."""
        return self.repository.list_all(
            page=page,
            page_size=page_size,
            search=search,
            identification_country_id=identification_country_id,
            identification_type=identification_type,
            verification_status=verification_status,
        )

    def get_by_id(
        self,
        person_identity_id: UUID,
    ) -> PersonIdentity:
        """Obtiene una identidad de persona por identificador.

        Args:
            person_identity_id: Identificador de la persona.

        Returns:
            Identidad encontrada.

        Raises:
            PersonIdentityNotFoundError: Si no existe.
        """
        person_identity = self.repository.get_by_id(
            person_identity_id,
        )

        if person_identity is None:
            raise PersonIdentityNotFoundError

        return person_identity

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
        identification_number = self._validate_identification_number(
            identification_country_id=identification_country_id,
            identification_type=identification_type,
            identification_number=identification_number,
        )

        return self.repository.create(
            identification_country_id=identification_country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            second_last_name=second_last_name,
            birth_date=birth_date,
            verification_status=verification_status,
            actor_id=actor_id,
        )

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
    ) -> PersonIdentity:
        """Actualiza completamente una identidad global de persona."""
        identification_number = self._validate_identification_number(
            identification_country_id=identification_country_id,
            identification_type=identification_type,
            identification_number=identification_number,
        )

        person_identity = self.repository.update(
            person_identity_id,
            expected_version=expected_version,
            identification_country_id=identification_country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            second_last_name=second_last_name,
            birth_date=birth_date,
            verification_status=verification_status,
            actor_id=actor_id,
        )

        if person_identity is None:
            raise PersonIdentityNotFoundError

        return person_identity

    def _validate_identification_number(
        self,
        *,
        identification_country_id: UUID,
        identification_type: PersonIdentificationType,
        identification_number: str,
    ) -> str:
        """Valida el número según país y tipo cuando existe una regla.

        Args:
            identification_country_id: UUID externo del país.
            identification_type: Tipo de identificación.
            identification_number: Número recibido desde la API.

        Returns:
            Número normalizado.

        Raises:
            InvalidIdentificationNumberError: Si existe regla aplicable
                y el número no la cumple.
        """
        normalized_number = normalize_identification_number(
            identification_number,
        )

        rule = self.identification_rules.get_rule(
            country_id=identification_country_id,
            identification_type=identification_type,
        )

        if rule is not None and not rule.validate(normalized_number):
            raise InvalidIdentificationNumberError(
                rule.description,
            )

        return normalized_number
