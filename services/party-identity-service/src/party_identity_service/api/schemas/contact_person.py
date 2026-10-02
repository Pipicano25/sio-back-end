"""Schemas HTTP de personas de contacto (contracts/rest-api.md §2)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from party_identity_service.api.schemas.contact_profile import Email, Phone, TrimmedOptional

Position = Annotated[Annotated[str, StringConstraints(max_length=120)] | None, TrimmedOptional]


class ContactPersonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_identity_id: UUID | None = None
    position: Position = None
    email: Email = None
    phone: Phone = None
    is_primary: bool = False


class ContactPersonUpdate(BaseModel):
    """`is_primary` y `organization_identity_id` se aceptan solo para responder
    `IMMUTABLE_FIELD` (regla 4.2); nunca se aplican."""

    model_config = ConfigDict(extra="forbid")

    person_identity_id: UUID | None = None
    position: Position = None
    email: Email = None
    phone: Phone = None
    version: int = Field(ge=1)
    is_primary: bool | None = Field(default=None, description="No modificable por PUT; use set-primary.")
    organization_identity_id: UUID | None = Field(default=None, description="Inmutable.")


class VersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)


class ContactPersonResponse(BaseModel):
    """Incluye los campos garantizados del contrato Provider (FR-080)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_identity_id: UUID
    person_identity_id: UUID | None
    position: str | None
    email: str | None
    phone: str | None
    is_primary: bool
    is_active: bool
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
