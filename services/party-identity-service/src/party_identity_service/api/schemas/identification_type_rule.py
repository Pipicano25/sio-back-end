"""Schemas HTTP para reglas de tipos de identificación.

Las validaciones de dominio (patrón compilable, ejemplo, rangos de edad y
vigencia, inmutabilidad) las hace el servicio de aplicación, que emite códigos
estables (`INVALID_NUMBER_PATTERN`, `RULE_CHANGE_REQUIRES_NEW_VERSION`, ...).
Aquí solo se valida la forma de la solicitud.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

PartyKindCode = Literal[
    "PERSON",
    "ORGANIZATION",
]

NumberPattern = Annotated[
    str,
    Field(
        min_length=1,
        max_length=300,
        description="Expresión regular usada para validar el número.",
    ),
]

IdentificationTypeCode = Annotated[
    str,
    Field(
        min_length=1,
        max_length=40,
    ),
]

IdentificationSiglaCode = Annotated[
    str,
    Field(
        min_length=1,
        max_length=10,
    ),
]

RuleDescription = Annotated[
    str,
    Field(
        min_length=1,
        max_length=1000,
        description="Descripción funcional de la regla.",
    ),
]

ExampleValue = Annotated[
    str | None,
    Field(
        max_length=40,
    ),
]

AgeYears = Annotated[
    int | None,
    Field(
        le=150,
        description="Edad en años; no negativa.",
    ),
]

Version = Annotated[
    int,
    Field(
        ge=1,
        description="Versión conocida por el cliente.",
    ),
]


class IdentificationTypeRuleCreate(BaseModel):
    """Payload para crear una regla activa."""

    model_config = ConfigDict(
        extra="forbid",
    )

    party_kind: PartyKindCode
    country_id: UUID
    identification_type: IdentificationTypeCode
    sigla: IdentificationSiglaCode
    number_pattern: NumberPattern
    number_pattern_description: RuleDescription
    example_value: ExampleValue = None
    min_age_years: AgeYears = None
    max_age_years: AgeYears = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None


class IdentificationTypeRuleUpdate(BaseModel):
    """Payload de modificación ordinaria: solo descripción y ejemplo (FR-013).

    Los campos de identidad y los semánticos se aceptan únicamente para
    detectarlos: si difieren del valor vigente se responde `IMMUTABLE_FIELD`
    o `RULE_CHANGE_REQUIRES_NEW_VERSION`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    number_pattern_description: RuleDescription
    example_value: ExampleValue = None
    version: Version
    party_kind: PartyKindCode | None = None
    country_id: UUID | None = None
    identification_type: IdentificationTypeCode | None = None
    sigla: IdentificationSiglaCode | None = None
    number_pattern: NumberPattern | None = None
    min_age_years: AgeYears = None
    max_age_years: AgeYears = None


class IdentificationTypeRuleVersionCreate(BaseModel):
    """Payload para crear una nueva versión de una regla activa (DS-07)."""

    model_config = ConfigDict(
        extra="forbid",
    )

    number_pattern: NumberPattern
    number_pattern_description: RuleDescription
    example_value: ExampleValue = None
    min_age_years: AgeYears = None
    max_age_years: AgeYears = None
    version: Version


class IdentificationTypeRuleResponse(BaseModel):
    """Respuesta HTTP de una regla de identificación."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    party_kind: str
    country_id: UUID
    identification_type: str
    sigla: str
    number_pattern: str
    number_pattern_description: str
    example_value: str | None
    min_age_years: int | None
    max_age_years: int | None
    is_active: bool
    valid_from: datetime
    valid_to: datetime | None
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
