"""Contratos usados por la capa de aplicación."""

from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from party_identity_service.application.identification_rules import (
    IdentificationRule,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.identification_type_rule import (
    IdentificationType,
    IdentificationTypeRule,
    IdentificationSigla,
    PartyKind,
)
from party_identity_service.domain.person_identity import (
    PersonIdentificationType,
    PersonIdentity,
    PersonVerificationStatus,
)


class CountryValidator(Protocol):
    """Define validación de países externos."""

    def exists(
        self,
        country_id: UUID,
    ) -> bool:
        """Indica si el país existe en Geography Service."""
        ...


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


class IdentificationTypeRuleRepository(Protocol):
    """Define operaciones de persistencia para reglas de identificación."""

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        party_kind: PartyKind | None,
        country_id: UUID | None,
        identification_type: IdentificationType | None,
        sigla: IdentificationSigla | None,
        is_active: bool | None,
    ) -> PageResult[IdentificationTypeRule]:
        """Obtiene una página filtrada de reglas de identificación."""
        ...

    def get_by_id(
        self,
        rule_id: UUID,
    ) -> IdentificationTypeRule | None:
        """Obtiene una regla por identificador."""
        ...

    def create(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
        identification_type: IdentificationType,
        sigla: IdentificationSigla,
        number_pattern: str,
        number_pattern_description: str,
        example_value: str | None,
        min_age_years: int | None,
        max_age_years: int | None,
        is_active: bool,
        valid_from: datetime | None,
        valid_to: datetime | None,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Crea una regla de identificación."""
        ...

    def update(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        party_kind: PartyKind,
        country_id: UUID,
        identification_type: IdentificationType,
        sigla: IdentificationSigla,
        number_pattern: str,
        number_pattern_description: str,
        example_value: str | None,
        min_age_years: int | None,
        max_age_years: int | None,
        is_active: bool,
        valid_from: datetime | None,
        valid_to: datetime | None,
        actor_id: str,
    ) -> IdentificationTypeRule | None:
        """Actualiza completamente una regla de identificación."""
        ...

    def get_active_rule(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
        identification_type: PersonIdentificationType,
    ) -> IdentificationRule | None:
        """Obtiene la regla activa para parte, país y tipo.

        Args:
            party_kind: Tipo de parte que usa la regla.
            country_id: UUID externo del país.
            identification_type: Tipo de identificación.

        Returns:
            Regla activa o None cuando no existe una regla vigente.
        """
        ...

    def list_active_rules_by_sigla(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
        sigla: IdentificationSigla,
    ) -> list[IdentificationRule]:
        """Obtiene reglas activas por país y sigla."""
        ...

    def has_active_rules(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
    ) -> bool:
        """Indica si un país tiene reglas activas para un tipo de parte."""
        ...
