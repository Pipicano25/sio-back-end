"""Schemas HTTP para identidades globales de organizaciones."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


IdentificationNumber = Annotated[
    str,
    Field(
        min_length=1,
        max_length=40,
        description="Número de identificación normalizado.",
    ),
]

IdentificationTypeCode = Annotated[
    str,
    Field(
        min_length=1,
        max_length=40,
        description="Sigla o tipo de identificación usado para validar.",
    ),
]

OrganizationName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=200,
    ),
]

OptionalOrganizationName = Annotated[
    str | None,
    Field(
        max_length=200,
    ),
]

OrganizationType = Annotated[
    str | None,
    Field(
        max_length=40,
    ),
]

RegistrationStatus = Annotated[
    str | None,
    Field(
        max_length=30,
    ),
]

Website = Annotated[
    str | None,
    Field(
        max_length=300,
    ),
]


class OrganizationIdentityCreate(BaseModel):
    """Payload para crear una identidad global de organización."""

    country_id: UUID
    identification_type: IdentificationTypeCode
    identification_number: IdentificationNumber
    legal_name: OrganizationName
    trade_name: OptionalOrganizationName = None
    organization_type: OrganizationType = None
    registration_status: RegistrationStatus = None
    website: Website = None


class OrganizationIdentityUpdate(BaseModel):
    """Payload para actualización completa de organización."""

    country_id: UUID
    identification_type: IdentificationTypeCode
    identification_number: IdentificationNumber
    legal_name: OrganizationName
    trade_name: OptionalOrganizationName = None
    organization_type: OrganizationType = None
    registration_status: RegistrationStatus = None
    website: Website = None
    version: int = Field(
        ge=1,
        description="Versión conocida por el cliente.",
    )


class OrganizationIdentityResponse(BaseModel):
    """Respuesta HTTP de una identidad global de organización."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    country_id: UUID
    identification_type: str
    identification_number: str
    legal_name: str
    trade_name: str | None
    organization_type: str | None
    registration_status: str | None
    website: str | None
    version: int
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
