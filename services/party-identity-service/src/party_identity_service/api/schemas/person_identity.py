"""Schemas HTTP para identidades globales de personas."""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from party_identity_service.domain.person_identity import (
    PersonIdentificationType,
    PersonVerificationStatus,
)


IdentificationNumber = Annotated[
    str,
    Field(
        min_length=1,
        max_length=40,
        description="Número de identificación normalizado.",
    ),
]

PersonName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=100,
    ),
]

OptionalPersonName = Annotated[
    str | None,
    Field(
        max_length=100,
    ),
]


class PersonIdentityCreate(BaseModel):
    """Payload para crear una identidad global de persona."""

    identification_country_id: UUID
    identification_type: PersonIdentificationType
    identification_number: IdentificationNumber
    first_name: PersonName
    middle_name: OptionalPersonName = None
    last_name: PersonName
    second_last_name: OptionalPersonName = None
    birth_date: date | None = None
    verification_status: PersonVerificationStatus = "UNVERIFIED"


class PersonIdentityUpdate(BaseModel):
    """Payload para actualización completa de persona."""

    identification_country_id: UUID
    identification_type: PersonIdentificationType
    identification_number: IdentificationNumber
    first_name: PersonName
    middle_name: OptionalPersonName = None
    last_name: PersonName
    second_last_name: OptionalPersonName = None
    birth_date: date | None = None
    verification_status: PersonVerificationStatus
    version: int = Field(
        ge=1,
        description="Versión conocida por el cliente.",
    )


class PersonIdentityResponse(BaseModel):
    """Respuesta HTTP de una identidad global de persona."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    identification_country_id: UUID
    identification_type: PersonIdentificationType
    identification_number: str
    first_name: str
    middle_name: str | None
    last_name: str
    second_last_name: str | None
    birth_date: date | None
    verification_status: PersonVerificationStatus
    version: int
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
