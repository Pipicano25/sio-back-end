"""Reglas de validación para números de identificación."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from uuid import UUID

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
