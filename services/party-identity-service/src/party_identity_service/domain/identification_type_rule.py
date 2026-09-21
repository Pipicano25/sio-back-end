"""Entidad de dominio para reglas de tipos de identificación."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


PartyKind = str
IdentificationType = str
IdentificationSigla = str


@dataclass(frozen=True, slots=True)
class IdentificationTypeRule:
    """Representa una regla parametrizada de identificación.

    Attributes:
        id: Identificador de la regla.
        party_kind: Tipo de parte a la que aplica la regla.
        country_id: País externo al que aplica la regla.
        identification_type: Tipo de identificación validado.
        sigla: Sigla oficial del tipo de documento.
        number_pattern: Expresión regular que debe cumplir el número.
        number_pattern_description: Mensaje funcional de la regla.
        example_value: Ejemplo de número válido.
        min_age_years: Edad mínima permitida.
        max_age_years: Edad máxima permitida.
        is_active: Indica si la regla está activa.
        valid_from: Fecha inicial de vigencia.
        valid_to: Fecha final de vigencia, cuando aplique.
        version: Versión para concurrencia optimista.
        created_by: Usuario que creó el registro.
        updated_by: Usuario que realizó la última modificación.
        created_at: Fecha de creación.
        updated_at: Fecha de última modificación.
    """

    id: UUID
    party_kind: PartyKind
    country_id: UUID
    identification_type: IdentificationType
    sigla: IdentificationSigla
    number_pattern: str
    number_pattern_description: str
    example_value: str | None
    min_age_years: int | None
    max_age_years: int | None
    is_active: bool
    valid_from: datetime
    valid_to: datetime | None
    version: int
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
