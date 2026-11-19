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
    UnsupportedIdentificationTypeError,
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


NIT_SIGLA = "NIT"

# Pesos de la DIAN para el dígito de verificación del NIT, de derecha a izquierda.
NIT_WEIGHTS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


def nit_check_digit(base: str) -> int:
    """Calcula el dígito de verificación de un NIT colombiano (módulo 11 de la DIAN).

    Cada dígito de la base, de derecha a izquierda, se multiplica por su peso; se suma y se toma
    el residuo entre 11. Si el residuo es 0 o 1, ese es el dígito; si no, 11 menos el residuo.

    Args:
        base: Dígitos del NIT antes del guion (máximo 15).

    Returns:
        Dígito de verificación esperado.
    """
    total = sum(
        int(digit) * weight
        for digit, weight in zip(reversed(base), NIT_WEIGHTS)
    )
    remainder = total % 11
    return remainder if remainder < 2 else 11 - remainder


def validate_nit_check_digit(identification_number: str) -> None:
    """Rechaza un NIT `base-dígito` cuyo dígito de verificación no corresponde a la base.

    Raises:
        InvalidIdentificationNumberError: Si el formato no es `dígitos-dígito` o el dígito no cuadra.
    """
    match = re.fullmatch(r"([0-9]{1,15})-([0-9])", identification_number)

    if match is None:
        raise InvalidIdentificationNumberError(
            "El NIT debe tener solo dígitos, un guion y el dígito de verificación."
        )

    base, digit = match.group(1), int(match.group(2))
    expected = nit_check_digit(base)

    if digit != expected:
        raise InvalidIdentificationNumberError(
            f"El dígito de verificación del NIT no es válido: para la base {base} "
            f"corresponde {expected}, no {digit}."
        )


def match_identification_number(
    rules: list[IdentificationRule],
    identification_number: str,
    sigla: str | None = None,
) -> list[IdentificationRule]:
    """Devuelve las reglas activas de la sigla que el número cumple.

    Solo se aceptan siglas con al menos una regla activa para el tipo de parte
    y el país (DS-03, enmienda del 2026-11-18): sin reglas, la identificación
    se rechaza, también en un país que no tiene ninguna regla.

    Args:
        rules: Reglas activas del tipo de parte, país y sigla.
        identification_number: Número ya normalizado.
        sigla: Sigla recibida, solo para el mensaje de error.

    Con la sigla `NIT`, además del patrón se exige el dígito de verificación de la DIAN
    (enmienda del 2026-11-18).

    Returns:
        Reglas cumplidas (nunca vacía).

    Raises:
        UnsupportedIdentificationTypeError: Si no hay reglas para la sigla.
        InvalidIdentificationNumberError: Si hay reglas y no cumple ninguna, o si el dígito de
            verificación del NIT no corresponde.
    """
    if not rules:
        raise UnsupportedIdentificationTypeError(
            f"La sigla {sigla!r} no tiene una regla activa para este tipo de parte en el país indicado. "
            "Consulte las siglas permitidas en identification-type-rules."
            if sigla
            else None
        )

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

    if any(rule.sigla == NIT_SIGLA for rule in matching):
        validate_nit_check_digit(identification_number)

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
