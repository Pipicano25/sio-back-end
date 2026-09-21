"""Casos de uso para reglas de tipos de identificación."""

from datetime import datetime
from uuid import UUID

from party_identity_service.application.exceptions import (
    CountryNotFoundError,
    IdentificationTypeRuleConflictError,
    IdentificationTypeRuleNotFoundError,
    IdentificationTypeRuleVersionConflictError,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.application.ports import (
    CountryValidator,
    IdentificationTypeRuleRepository,
)
from party_identity_service.domain.identification_type_rule import (
    IdentificationType,
    IdentificationTypeRule,
    IdentificationSigla,
    PartyKind,
)


class IdentificationTypeRuleService:
    """Orquesta casos de uso de reglas de identificación."""

    def __init__(
        self,
        repository: IdentificationTypeRuleRepository,
        country_validator: CountryValidator,
    ) -> None:
        """Inicializa el servicio de aplicación.

        Args:
            repository: Puerto de persistencia de reglas.
        """
        self.repository = repository
        self.country_validator = country_validator

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        party_kind: PartyKind | None = None,
        country_id: UUID | None = None,
        identification_type: IdentificationType | None = None,
        sigla: IdentificationSigla | None = None,
        is_active: bool | None = None,
    ) -> PageResult[IdentificationTypeRule]:
        """Obtiene reglas de identificación con paginación y filtros."""
        return self.repository.list_all(
            page=page,
            page_size=page_size,
            party_kind=party_kind,
            country_id=country_id,
            identification_type=identification_type,
            sigla=sigla,
            is_active=is_active,
        )

    def get_by_id(
        self,
        rule_id: UUID,
    ) -> IdentificationTypeRule:
        """Obtiene una regla por identificador."""
        rule = self.repository.get_by_id(
            rule_id,
        )

        if rule is None:
            raise IdentificationTypeRuleNotFoundError

        return rule

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
        self._validate_country(
            country_id,
        )
        return self.repository.create(
            party_kind=party_kind,
            country_id=country_id,
            identification_type=identification_type,
            sigla=sigla,
            number_pattern=number_pattern,
            number_pattern_description=number_pattern_description,
            example_value=example_value,
            min_age_years=min_age_years,
            max_age_years=max_age_years,
            is_active=is_active,
            valid_from=valid_from,
            valid_to=valid_to,
            actor_id=actor_id,
        )

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
    ) -> IdentificationTypeRule:
        """Actualiza completamente una regla de identificación."""
        self._validate_country(
            country_id,
        )
        rule = self.repository.update(
            rule_id,
            expected_version=expected_version,
            party_kind=party_kind,
            country_id=country_id,
            identification_type=identification_type,
            sigla=sigla,
            number_pattern=number_pattern,
            number_pattern_description=number_pattern_description,
            example_value=example_value,
            min_age_years=min_age_years,
            max_age_years=max_age_years,
            is_active=is_active,
            valid_from=valid_from,
            valid_to=valid_to,
            actor_id=actor_id,
        )

        if rule is None:
            raise IdentificationTypeRuleNotFoundError

        return rule

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
