"""Schemas HTTP de perfiles de contacto (contracts/rest-api.md §1)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
PHONE_PATTERN = r"^[0-9 +\-()]+$"


def _trim(value: Any) -> Any:
    """Recorta cadenas; una cadena vacía equivale a `None` (FR-014, FR-015)."""
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return value


TrimmedOptional = BeforeValidator(_trim)

Email = Annotated[
    Annotated[str, StringConstraints(max_length=254, pattern=EMAIL_PATTERN)] | None,
    TrimmedOptional,
]
Phone = Annotated[
    Annotated[str, StringConstraints(max_length=40, pattern=PHONE_PATTERN)] | None,
    TrimmedOptional,
]
OptionalText = Annotated[str | None, TrimmedOptional]
PostalCode = Annotated[
    Annotated[str, StringConstraints(max_length=20)] | None,
    TrimmedOptional,
]


class ContactProfileCreate(BaseModel):
    """Versión nueva del perfil. `confirmed_by_user_id` no se admite (FR-026)."""

    model_config = ConfigDict(extra="forbid")

    email: Email = None
    phone: Phone = None
    address_line: OptionalText = None
    country_id: UUID | None = None
    administrative_division_id: UUID | None = None
    city_id: UUID | None = None
    postal_code: PostalCode = None
    confirmed_by_company_id: UUID
    version: int | None = Field(
        default=None,
        ge=1,
        description="Versión de la vigente; obligatoria si existe, ignorada si no.",
    )


class ContactProfileClose(BaseModel):
    """Cierre explícito de la versión vigente (DS-03)."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1, description="Versión de la vigente.")


class _ContactProfileResponseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    phone: str | None
    address_line: str | None
    country_id: UUID | None
    administrative_division_id: UUID | None
    city_id: UUID | None
    postal_code: str | None
    is_active: bool
    valid_from: datetime
    valid_to: datetime | None
    confirmed_by_company_id: UUID
    confirmed_by_user_id: UUID
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class PersonContactProfileResponse(_ContactProfileResponseBase):
    person_identity_id: UUID

    @classmethod
    def of(cls, profile) -> "PersonContactProfileResponse":
        return cls.model_validate({**_fields(profile), "person_identity_id": profile.owner_id})


class OrganizationContactProfileResponse(_ContactProfileResponseBase):
    organization_identity_id: UUID

    @classmethod
    def of(cls, profile) -> "OrganizationContactProfileResponse":
        return cls.model_validate({**_fields(profile), "organization_identity_id": profile.owner_id})


def _fields(profile) -> dict[str, Any]:
    return {name: getattr(profile, name) for name in _ContactProfileResponseBase.model_fields}
