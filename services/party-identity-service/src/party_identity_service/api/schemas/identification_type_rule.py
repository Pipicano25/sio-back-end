"""Schemas HTTP para reglas de tipos de identificación."""

from datetime import datetime
import re
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from party_identity_service.domain.identification_type_rule import (
    IdentificationType,
    IdentificationSigla,
    PartyKind,
)


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


class IdentificationTypeRuleBase(BaseModel):
    """Campos compartidos para crear y actualizar reglas."""

    party_kind: PartyKind
    country_id: UUID
    identification_type: IdentificationTypeCode
    sigla: IdentificationSiglaCode
    number_pattern: NumberPattern
    number_pattern_description: RuleDescription
    example_value: str | None = Field(
        default=None,
        max_length=40,
    )
    min_age_years: int | None = Field(
        default=None,
        ge=0,
        le=150,
        description="Edad mínima permitida para usar este documento.",
    )
    max_age_years: int | None = Field(
        default=None,
        ge=0,
        le=150,
        description="Edad máxima permitida para usar este documento.",
    )
    is_active: bool = True
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    @field_validator("number_pattern")
    @classmethod
    def validate_number_pattern(
        cls,
        value: str,
    ) -> str:
        """Valida que el patrón recibido sea una expresión regular válida."""
        pattern = value.strip()

        try:
            re.compile(pattern)

        except re.error as exc:
            raise ValueError(
                f"El patrón de número no es una expresión regular válida: {exc}"
            ) from exc

        return pattern

    @field_validator("party_kind", "identification_type", "sigla")
    @classmethod
    def normalize_codes(
        cls,
        value: str,
    ) -> str:
        """Normaliza códigos a mayúsculas."""
        return value.strip().upper()

    @field_validator("number_pattern_description")
    @classmethod
    def normalize_description(
        cls,
        value: str,
    ) -> str:
        """Normaliza la descripción de la regla."""
        return value.strip()

    @field_validator("example_value")
    @classmethod
    def normalize_example_value(
        cls,
        value: str | None,
    ) -> str | None:
        """Normaliza el ejemplo cuando fue informado."""
        if value is None:
            return None

        example_value = value.strip().upper()

        return example_value or None

    @model_validator(mode="after")
    def validate_validity_range(
        self,
    ) -> "IdentificationTypeRuleBase":
        """Valida que el rango de vigencia sea coherente."""
        if self.valid_to is not None and self.valid_from is not None:
            if self.valid_to <= self.valid_from:
                raise ValueError(
                    "valid_to debe ser posterior a valid_from."
                )

        if self.min_age_years is not None and self.max_age_years is not None:
            if self.max_age_years < self.min_age_years:
                raise ValueError(
                    "max_age_years debe ser mayor o igual a min_age_years."
                )

        return self


class IdentificationTypeRuleCreate(IdentificationTypeRuleBase):
    """Payload para crear una regla de identificación."""


class IdentificationTypeRuleUpdate(IdentificationTypeRuleBase):
    """Payload para actualización completa de regla."""

    version: int = Field(
        ge=1,
        description="Versión conocida por el cliente.",
    )


class IdentificationTypeRuleResponse(BaseModel):
    """Respuesta HTTP de una regla de identificación."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    party_kind: PartyKind
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
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
