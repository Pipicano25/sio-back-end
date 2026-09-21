"""Casos de uso para identidades globales de personas."""

from datetime import date
from uuid import UUID

from party_identity_service.application.exceptions import (
    CountryNotFoundError,
    InvalidIdentificationAgeError,
    InvalidIdentificationNumberError,
    PersonIdentityNotFoundError,
)
from party_identity_service.application.identification_rules import (
    normalize_identification_number,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.application.ports import (
    CountryValidator,
    IdentificationTypeRuleRepository,
    PersonIdentityRepository,
)
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
        identification_rule_repository: IdentificationTypeRuleRepository,
        country_validator: CountryValidator,
    ) -> None:
        """Inicializa el servicio de aplicación.

        Args:
            repository: Puerto de persistencia de identidades de persona.
            identification_rule_repository: Puerto de reglas de
                identificación.
        """
        self.repository = repository
        self.identification_rule_repository = identification_rule_repository
        self.country_validator = country_validator

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
        self._validate_country(
            identification_country_id,
        )
        identification_type = identification_type.strip().upper()
        identification_number = self._validate_identification_number(
            identification_country_id=identification_country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            birth_date=birth_date,
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
        self._validate_country(
            identification_country_id,
        )
        identification_type = identification_type.strip().upper()
        identification_number = self._validate_identification_number(
            identification_country_id=identification_country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            birth_date=birth_date,
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

    def _validate_country(
        self,
        country_id: UUID,
    ) -> None:
        """Valida que el país exista en Geography Service."""
        if not self.country_validator.exists(
            country_id,
        ):
            raise CountryNotFoundError(
                "El país indicado no existe en Geography Service."
            )

    def _validate_identification_number(
        self,
        *,
        identification_country_id: UUID,
        identification_type: PersonIdentificationType,
        identification_number: str,
        birth_date: date | None,
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
            InvalidIdentificationAgeError: Si existe regla aplicable
                con rango de edad y la persona no lo cumple.
        """
        normalized_number = normalize_identification_number(
            identification_number,
        )
        normalized_identification_type = identification_type.strip().upper()

        rules = self.identification_rule_repository.list_active_rules_by_sigla(
            party_kind="PERSON",
            country_id=identification_country_id,
            sigla=normalized_identification_type,
        )

        if not rules:
            has_country_rules = (
                self.identification_rule_repository.has_active_rules(
                    party_kind="PERSON",
                    country_id=identification_country_id,
                )
            )

            if has_country_rules:
                raise InvalidIdentificationNumberError(
                    "No existe una regla activa para el país y tipo "
                    "de identificación indicados."
                )

            return normalized_number

        matching_rules = [
            rule
            for rule in rules
            if rule.validate(
                normalized_number,
            )
        ]

        if not matching_rules:
            raise InvalidIdentificationNumberError(
                "El número de identificación no cumple ninguna regla "
                "activa para la sigla indicada."
            )

        age_rules = [
            rule
            for rule in matching_rules
            if rule.requires_birth_date()
        ]

        if age_rules:
            if birth_date is None:
                raise InvalidIdentificationAgeError(
                    "La fecha de nacimiento es obligatoria para validar "
                    "el rango de edad del tipo de identificación."
                )

            if not any(
                rule.validate_age(
                    birth_date,
                )
                for rule in age_rules
            ):
                raise InvalidIdentificationAgeError(
                    "La edad de la persona no cumple el rango permitido "
                    "para el tipo de identificación."
                )

        return normalized_number
