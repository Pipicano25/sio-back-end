"""Casos de uso para reglas de tipos de identificación."""

import re
from datetime import datetime
from uuid import UUID

from party_identity_service.application.exceptions import (
    CountryNotFoundError,
    ExampleDoesNotMatchPatternError,
    ImmutableFieldError,
    InvalidAgeRangeError,
    InvalidNumberPatternError,
    InvalidStatusTransitionError,
    InvalidValidityRangeError,
    NotFoundError,
    RuleChangeRequiresNewVersionError,
    VersionConflictError,
)
from party_identity_service.application.identification_rules import (
    normalize_code,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.application.ports import (
    CountryDirectory,
    IdentificationTypeRuleRepository,
)
from party_identity_service.domain.identification_type_rule import (
    IdentificationSigla,
    IdentificationType,
    IdentificationTypeRule,
    PartyKind,
)

IDENTITY_FIELDS = (
    "party_kind",
    "country_id",
    "identification_type",
    "sigla",
)
SEMANTIC_FIELDS = (
    "number_pattern",
    "min_age_years",
    "max_age_years",
)


def normalize_pattern(number_pattern: str) -> str:
    """Normaliza y valida una expresión regular de regla.

    Raises:
        InvalidNumberPatternError: Si está vacía o no compila.
    """
    pattern = number_pattern.strip()

    if not pattern:
        raise InvalidNumberPatternError("El patrón de número no puede estar vacío.")

    try:
        re.compile(pattern)

    except re.error as exc:
        raise InvalidNumberPatternError(
            f"El patrón de número no es una expresión regular válida: {exc}"
        ) from None

    return pattern


def normalize_example(example_value: str | None) -> str | None:
    """Normaliza el ejemplo de una regla; vacío equivale a ausente."""
    if example_value is None:
        return None

    return example_value.strip().upper() or None


def validate_example(
    number_pattern: str,
    example_value: str | None,
) -> None:
    """Exige que el ejemplo, si existe, cumpla el patrón."""
    if example_value is not None and re.fullmatch(number_pattern, example_value) is None:
        raise ExampleDoesNotMatchPatternError


def validate_age_range(
    min_age_years: int | None,
    max_age_years: int | None,
) -> None:
    """Exige edades no negativas y máximo mayor o igual al mínimo."""
    if (min_age_years is not None and min_age_years < 0) or (
        max_age_years is not None and max_age_years < 0
    ):
        raise InvalidAgeRangeError("Las edades no pueden ser negativas.")

    if (
        min_age_years is not None
        and max_age_years is not None
        and max_age_years < min_age_years
    ):
        raise InvalidAgeRangeError


class IdentificationTypeRuleService:
    """Orquesta casos de uso de reglas de identificación (DS-07)."""

    def __init__(
        self,
        repository: IdentificationTypeRuleRepository,
        country_directory: CountryDirectory,
    ) -> None:
        """Inicializa el servicio de aplicación.

        Args:
            repository: Puerto de persistencia de reglas.
            country_directory: Puerto hacia Geography Service.
        """
        self.repository = repository
        self.country_directory = country_directory

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
            identification_type=(
                normalize_code(identification_type)
                if identification_type
                else None
            ),
            sigla=normalize_code(sigla) if sigla else None,
            is_active=is_active,
        )

    def get_by_id(
        self,
        rule_id: UUID,
    ) -> IdentificationTypeRule:
        """Obtiene una regla por identificador.

        Raises:
            NotFoundError: Si no existe.
        """
        rule = self.repository.get_by_id(rule_id)

        if rule is None:
            raise NotFoundError("La regla solicitada no existe.")

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
        valid_from: datetime | None,
        valid_to: datetime | None,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Crea una regla activa (FR-011, FR-012)."""
        number_pattern = normalize_pattern(number_pattern)
        example_value = normalize_example(example_value)
        validate_example(number_pattern, example_value)
        validate_age_range(min_age_years, max_age_years)

        if valid_from is not None and valid_to is not None and valid_to <= valid_from:
            raise InvalidValidityRangeError

        self._validate_country(country_id)

        return self.repository.create(
            party_kind=party_kind,
            country_id=country_id,
            identification_type=normalize_code(identification_type),
            sigla=normalize_code(sigla),
            number_pattern=number_pattern,
            number_pattern_description=number_pattern_description.strip(),
            example_value=example_value,
            min_age_years=min_age_years,
            max_age_years=max_age_years,
            valid_from=valid_from,
            valid_to=valid_to,
            actor_id=actor_id,
        )

    def update(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        number_pattern_description: str,
        example_value: str | None,
        requested_identity: dict[str, object] | None = None,
        requested_semantics: dict[str, object] | None = None,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Modifica en sitio solo la descripción y el ejemplo (FR-013, FR-029).

        Args:
            requested_identity: Campos de identidad enviados en la solicitud,
                solo para rechazar su modificación.
            requested_semantics: Patrón o edades enviados en la solicitud, solo
                para exigir una nueva versión si difieren de los vigentes.
        """
        current = self.get_by_id(rule_id)

        if current.version != expected_version:
            raise VersionConflictError

        if not current.is_active:
            raise InvalidStatusTransitionError(
                "Una regla histórica no admite cambios."
            )

        for field, value in (requested_identity or {}).items():
            if value is not None and _normalized(field, value) != getattr(current, field):
                raise ImmutableFieldError(
                    f"El campo {field} de una regla no puede modificarse."
                )

        for field, value in (requested_semantics or {}).items():
            if _normalized(field, value) != getattr(current, field):
                raise RuleChangeRequiresNewVersionError

        changes = {
            field: value
            for field, value in {
                "number_pattern_description": number_pattern_description.strip(),
                "example_value": normalize_example(example_value),
            }.items()
            if getattr(current, field) != value
        }

        if not changes:
            return current

        validate_example(current.number_pattern, changes.get("example_value", current.example_value))

        return self.repository.update(
            rule_id,
            expected_version=expected_version,
            values=changes,
            actor_id=actor_id,
        )

    def create_version(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        number_pattern: str,
        number_pattern_description: str,
        example_value: str | None,
        min_age_years: int | None,
        max_age_years: int | None,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Cierra la regla vigente y crea su sucesora (DS-07, R-09).

        El país no cambia, por lo que no se consulta Geography.
        """
        current = self.get_by_id(rule_id)

        if current.version != expected_version:
            raise VersionConflictError

        if not current.is_active:
            raise InvalidStatusTransitionError(
                "Una regla histórica no admite nuevas versiones."
            )

        number_pattern = normalize_pattern(number_pattern)
        example_value = normalize_example(example_value)
        validate_example(number_pattern, example_value)
        validate_age_range(min_age_years, max_age_years)

        return self.repository.create_version(
            rule_id,
            expected_version=expected_version,
            number_pattern=number_pattern,
            number_pattern_description=number_pattern_description.strip(),
            example_value=example_value,
            min_age_years=min_age_years,
            max_age_years=max_age_years,
            actor_id=actor_id,
        )

    def deactivate(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Retira una regla sin eliminarla (FR-014)."""
        current = self.get_by_id(rule_id)

        if current.version != expected_version:
            raise VersionConflictError

        if not current.is_active:
            raise InvalidStatusTransitionError("La regla ya está retirada.")

        return self.repository.deactivate(
            rule_id,
            expected_version=expected_version,
            actor_id=actor_id,
        )

    def _validate_country(
        self,
        country_id: UUID,
    ) -> None:
        """Valida que el país exista en Geography Service."""
        if not self.country_directory.exists(country_id):
            raise CountryNotFoundError


def _normalized(field: str, value: object) -> object:
    """Normaliza un valor de solicitud para compararlo con el vigente."""
    if field in {"party_kind", "identification_type", "sigla"} and isinstance(value, str):
        return normalize_code(value)

    if field == "number_pattern" and isinstance(value, str):
        return value.strip()

    return value
