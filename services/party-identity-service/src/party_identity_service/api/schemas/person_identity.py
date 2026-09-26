"""Schemas HTTP para identidades globales de personas."""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from party_identity_service.domain.person_identity import (
    IdentityStatus,
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

IdentificationTypeCode = Annotated[
    str,
    Field(
        min_length=1,
        max_length=40,
        description="Sigla o tipo de identificación usado para validar.",
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
    """Payload para crear una identidad global de persona.

    No acepta `status` ni campos de auditoría (RC-10): se rechazan con `422`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    identification_country_id: UUID
    identification_type: IdentificationTypeCode
    identification_number: IdentificationNumber
    first_name: PersonName
    middle_name: OptionalPersonName = None
    last_name: PersonName
    second_last_name: OptionalPersonName = None
    birth_date: date | None = None
    verification_status: PersonVerificationStatus = "UNVERIFIED"


class PersonIdentityUpdate(BaseModel):
    """Payload para actualización completa de persona.

    El estado de uso solo cambia con las acciones `deactivate`/`reactivate`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    identification_country_id: UUID
    identification_type: IdentificationTypeCode
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
    identification_type: str
    identification_number: str
    first_name: str
    middle_name: str | None
    last_name: str
    second_last_name: str | None
    birth_date: date | None
    verification_status: PersonVerificationStatus
    status: IdentityStatus
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
