"""Reglas de validación para números de identificación."""

from __future__ import annotations

from dataclasses import dataclass
import re
from uuid import UUID

from party_identity_service.domain.person_identity import (
    PersonIdentificationType,
)


@dataclass(frozen=True, slots=True)
class IdentificationRule:
    """Regla aplicable a un país y tipo de identificación.

    Attributes:
        country_id: UUID externo del país.
        identification_type: Tipo de identificación.
        pattern: Expresión regular aceptada.
        description: Descripción funcional de la regla.
    """

    country_id: UUID
    identification_type: PersonIdentificationType
    pattern: str
    description: str

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


class IdentificationRuleSet:
    """Contenedor de reglas de validación de identificaciones."""

    def __init__(
        self,
        rules: list[IdentificationRule],
    ) -> None:
        """Inicializa el conjunto de reglas.

        Args:
            rules: Reglas disponibles para validación.
        """
        self._rules = {
            (
                rule.country_id,
                rule.identification_type,
            ): rule
            for rule in rules
        }

    def get_rule(
        self,
        *,
        country_id: UUID,
        identification_type: PersonIdentificationType,
    ) -> IdentificationRule | None:
        """Obtiene la regla aplicable a país y tipo.

        Args:
            country_id: UUID externo del país.
            identification_type: Tipo de identificación.

        Returns:
            Regla encontrada o None cuando no hay regla específica.
        """
        return self._rules.get(
            (
                country_id,
                identification_type,
            )
        )


def build_identification_rule_set(
    *,
    colombia_country_id: UUID | None,
) -> IdentificationRuleSet:
    """Construye las reglas de identificación configuradas.

    Args:
        colombia_country_id: UUID externo de Colombia. Si no se define,
            no se activan reglas específicas para Colombia.

    Returns:
        Conjunto de reglas disponibles.
    """
    rules: list[IdentificationRule] = []

    if colombia_country_id is not None:
        rules.extend(
            [
                IdentificationRule(
                    country_id=colombia_country_id,
                    identification_type="NATIONAL_ID",
                    pattern=r"[0-9]{6,10}",
                    description=(
                        "Colombia NATIONAL_ID acepta solo dígitos, "
                        "entre 6 y 10 caracteres."
                    ),
                ),
                IdentificationRule(
                    country_id=colombia_country_id,
                    identification_type="FOREIGN_ID",
                    pattern=r"[A-Z0-9]{3,20}",
                    description=(
                        "Colombia FOREIGN_ID acepta letras mayúsculas "
                        "y dígitos, entre 3 y 20 caracteres."
                    ),
                ),
                IdentificationRule(
                    country_id=colombia_country_id,
                    identification_type="PASSPORT",
                    pattern=r"[A-Z0-9]{6,20}",
                    description=(
                        "Colombia PASSPORT acepta letras mayúsculas "
                        "y dígitos, entre 6 y 20 caracteres."
                    ),
                ),
                IdentificationRule(
                    country_id=colombia_country_id,
                    identification_type="TAX_ID",
                    pattern=r"[0-9]{5,15}(-[0-9])?",
                    description=(
                        "Colombia TAX_ID acepta dígitos y, opcionalmente, "
                        "dígito de verificación separado por guion."
                    ),
                ),
            ]
        )

    return IdentificationRuleSet(
        rules,
    )


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
