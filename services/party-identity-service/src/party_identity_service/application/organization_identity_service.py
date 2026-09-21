"""Casos de uso para identidades globales de organizaciones."""

from uuid import UUID

from party_identity_service.application.exceptions import (
    CountryNotFoundError,
    InvalidIdentificationNumberError,
    OrganizationIdentityNotFoundError,
)
from party_identity_service.application.identification_rules import (
    normalize_identification_number,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.application.ports import (
    CountryValidator,
    IdentificationTypeRuleRepository,
    OrganizationIdentityRepository,
)
from party_identity_service.domain.organization_identity import (
    OrganizationIdentificationType,
    OrganizationIdentity,
)


class OrganizationIdentityService:
    """Orquesta casos de uso de identidades de organizaciones."""

    def __init__(
        self,
        repository: OrganizationIdentityRepository,
        identification_rule_repository: IdentificationTypeRuleRepository,
        country_validator: CountryValidator,
    ) -> None:
        """Inicializa el servicio de aplicación."""
        self.repository = repository
        self.identification_rule_repository = identification_rule_repository
        self.country_validator = country_validator

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        country_id: UUID | None = None,
        identification_type: OrganizationIdentificationType | None = None,
        registration_status: str | None = None,
    ) -> PageResult[OrganizationIdentity]:
        """Obtiene identidades de organización con paginación y filtros."""
        return self.repository.list_all(
            page=page,
            page_size=page_size,
            search=search,
            country_id=country_id,
            identification_type=identification_type,
            registration_status=registration_status,
        )

    def get_by_id(
        self,
        organization_identity_id: UUID,
    ) -> OrganizationIdentity:
        """Obtiene una identidad de organización por identificador."""
        organization_identity = self.repository.get_by_id(
            organization_identity_id,
        )

        if organization_identity is None:
            raise OrganizationIdentityNotFoundError

        return organization_identity

    def create(
        self,
        *,
        country_id: UUID,
        identification_type: OrganizationIdentificationType,
        identification_number: str,
        legal_name: str,
        trade_name: str | None,
        organization_type: str | None,
        registration_status: str | None,
        website: str | None,
        actor_id: str,
    ) -> OrganizationIdentity:
        """Crea una identidad global de organización."""
        self._validate_country(
            country_id,
        )
        identification_type = identification_type.strip().upper()
        identification_number = self._validate_identification_number(
            country_id=country_id,
            identification_type=identification_type,
            identification_number=identification_number,
        )

        return self.repository.create(
            country_id=country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            legal_name=legal_name,
            trade_name=trade_name,
            organization_type=organization_type,
            registration_status=registration_status,
            website=website,
            actor_id=actor_id,
        )

    def update(
        self,
        organization_identity_id: UUID,
        *,
        expected_version: int,
        country_id: UUID,
        identification_type: OrganizationIdentificationType,
        identification_number: str,
        legal_name: str,
        trade_name: str | None,
        organization_type: str | None,
        registration_status: str | None,
        website: str | None,
        actor_id: str,
    ) -> OrganizationIdentity:
        """Actualiza completamente una identidad global de organización."""
        self._validate_country(
            country_id,
        )
        identification_type = identification_type.strip().upper()
        identification_number = self._validate_identification_number(
            country_id=country_id,
            identification_type=identification_type,
            identification_number=identification_number,
        )

        organization_identity = self.repository.update(
            organization_identity_id,
            expected_version=expected_version,
            country_id=country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            legal_name=legal_name,
            trade_name=trade_name,
            organization_type=organization_type,
            registration_status=registration_status,
            website=website,
            actor_id=actor_id,
        )

        if organization_identity is None:
            raise OrganizationIdentityNotFoundError

        return organization_identity

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
        country_id: UUID,
        identification_type: OrganizationIdentificationType,
        identification_number: str,
    ) -> str:
        """Valida el número según reglas de organización por país y sigla."""
        normalized_number = normalize_identification_number(
            identification_number,
        )
        normalized_identification_type = identification_type.strip().upper()

        rules = self.identification_rule_repository.list_active_rules_by_sigla(
            party_kind="ORGANIZATION",
            country_id=country_id,
            sigla=normalized_identification_type,
        )

        if not rules:
            has_country_rules = (
                self.identification_rule_repository.has_active_rules(
                    party_kind="ORGANIZATION",
                    country_id=country_id,
                )
            )

            if has_country_rules:
                raise InvalidIdentificationNumberError(
                    "No existe una regla activa para el país y tipo "
                    "de identificación indicados."
                )

            return normalized_number

        if not any(
            rule.validate(
                normalized_number,
            )
            for rule in rules
        ):
            raise InvalidIdentificationNumberError(
                "El número de identificación no cumple ninguna regla "
                "activa para la sigla indicada."
            )

        return normalized_number
