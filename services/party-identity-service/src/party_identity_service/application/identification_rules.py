"""Reglas de validación para números de identificación."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import re
from uuid import UUID

from party_identity_service.application.exceptions import (
    AgeOutOfRangeError,
    BirthDateInFutureError,
    BirthDateRequiredError,
    InvalidIdentificationNumberError,
)

from party_identity_service.domain.identification_type_rule import (
    IdentificationType,
    IdentificationSigla,
    PartyKind,
)


@dataclass(frozen=True, slots=True)
class IdentificationRule:
    """Regla aplicable a una parte, país y tipo de identificación.

    Attributes:
        party_kind: Tipo de parte a la que aplica la regla.
        country_id: UUID externo del país.
        identification_type: Tipo de identificación.
        sigla: Sigla oficial del documento.
        pattern: Expresión regular aceptada.
        description: Descripción funcional de la regla.
        min_age_years: Edad mínima permitida.
        max_age_years: Edad máxima permitida.
    """

    party_kind: PartyKind
    country_id: UUID
    identification_type: IdentificationType
    sigla: IdentificationSigla
    pattern: str
    description: str
    min_age_years: int | None = None
    max_age_years: int | None = None

    def validate(
        self,
        identification_number: str,
    ) -> bool:
        """Evalúa si el número cumple la expresión regular.

        Args:
            identification_number: Número normalizado a validar.

        Returns:
            True cuando cumple la regla; False en caso contrario.
        """
        return re.fullmatch(
            self.pattern,
            identification_number,
        ) is not None

    def requires_birth_date(
        self,
    ) -> bool:
        """Indica si la regla necesita fecha de nacimiento."""
        return self.min_age_years is not None or self.max_age_years is not None

    def validate_age(
        self,
        birth_date: date,
        *,
        today: date | None = None,
    ) -> bool:
        """Evalúa si la edad cumple el rango configurado.

        Args:
            birth_date: Fecha de nacimiento de la persona.
            today: Fecha de referencia. Por defecto usa la fecha actual.

        Returns:
            True cuando la edad cumple la regla; False en caso contrario.
        """
        current_date = today or date.today()
        age = current_date.year - birth_date.year

        if (
            current_date.month,
            current_date.day,
        ) < (
            birth_date.month,
            birth_date.day,
        ):
            age -= 1

        if self.min_age_years is not None and age < self.min_age_years:
            return False

        if self.max_age_years is not None and age > self.max_age_years:
            return False

        return True


def normalize_identification_number(
    identification_number: str,
) -> str:
    """Normaliza superficialmente un número de identificación.

    Args:
        identification_number: Número recibido desde la API.

    Returns:
        Número sin espacios externos y con letras en mayúscula.
    """
    return identification_number.strip().upper()


def normalize_code(value: str) -> str:
    """Normaliza un código (tipo de identificación, sigla) a mayúsculas."""
    return value.strip().upper()


# Colombia no aplica horario de verano: America/Bogota es siempre UTC-5.
# Se usa un desfase fijo para no depender de la base tz del contenedor.
OPERATIONAL_TIMEZONE = timezone(timedelta(hours=-5), name="America/Bogota")


def operational_today() -> date:
    """Fecha actual en la zona horaria operativa (`America/Bogota`)."""
    return datetime.now(OPERATIONAL_TIMEZONE).date()


def match_identification_number(
    rules: list[IdentificationRule],
    identification_number: str,
) -> list[IdentificationRule]:
    """Devuelve las reglas activas de la sigla que el número cumple.

    Sin reglas para la sigla se aplican solo las validaciones base, aunque el
    país tenga reglas para otras siglas (DS-03).

    Args:
        rules: Reglas activas del tipo de parte, país y sigla.
        identification_number: Número ya normalizado.

    Returns:
        Reglas cumplidas (lista vacía si no hay reglas para la sigla).

    Raises:
        InvalidIdentificationNumberError: Si hay reglas y no cumple ninguna.
    """
    if not rules:
        return []

    matching = [
        rule
        for rule in rules
        if rule.validate(identification_number)
    ]

    if not matching:
        descriptions = "; ".join(
            dict.fromkeys(rule.description for rule in rules)
        )
        raise InvalidIdentificationNumberError(
            "El número de identificación no cumple ninguna regla activa para "
            f"la sigla indicada. {descriptions}".strip()
        )

    return matching


def validate_age(
    matching_rules: list[IdentificationRule],
    birth_date: date | None,
    *,
    today: date | None = None,
) -> None:
    """Valida la edad contra las reglas cumplidas que la exigen.

    Raises:
        BirthDateRequiredError: Si alguna regla exige edad y falta la fecha.
        AgeOutOfRangeError: Si la edad no cumple ninguna de esas reglas.
    """
    age_rules = [
        rule
        for rule in matching_rules
        if rule.requires_birth_date()
    ]

    if not age_rules:
        return

    if birth_date is None:
        raise BirthDateRequiredError

    reference = today or operational_today()

    if not any(
        rule.validate_age(birth_date, today=reference)
        for rule in age_rules
    ):
        raise AgeOutOfRangeError


def validate_birth_date(
    birth_date: date | None,
    *,
    today: date | None = None,
) -> None:
    """Rechaza una fecha de nacimiento posterior a hoy (RN-10)."""
    if birth_date is not None and birth_date > (today or operational_today()):
        raise BirthDateInFutureError
