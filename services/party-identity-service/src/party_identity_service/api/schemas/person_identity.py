"""Schemas HTTP para identidades globales de personas."""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from party_identity_service.api.schemas.partial import PartialUpdate

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


class PersonIdentityUpdate(PartialUpdate):
    """Actualización parcial de persona: solo los campos que cambian (D28).

    El estado de uso solo cambia con las acciones `deactivate`/`reactivate`.
    """

    not_nullable = frozenset({"identification_country_id", "identification_type", "identification_number", "first_name", "last_name", "verification_status"})

    identification_country_id: UUID | None = None
    identification_type: IdentificationTypeCode | None = None
    identification_number: IdentificationNumber | None = None
    first_name: PersonName | None = None
    middle_name: OptionalPersonName = None
    last_name: PersonName | None = None
    second_last_name: OptionalPersonName = None
    birth_date: date | None = None
    verification_status: PersonVerificationStatus | None = None


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
