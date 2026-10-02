"""Schemas HTTP de representantes legales (contracts/rest-api.md §5)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from party_identity_service.api.schemas.contact_person import Position
from party_identity_service.api.schemas.contact_profile import TrimmedOptional

DocumentReference = Annotated[
    Annotated[str, StringConstraints(max_length=1000)] | None,
    TrimmedOptional,
]
RepresentativeTypeField = Literal["PRIMARY", "ALTERNATE", "OTHER"]


class LegalRepresentativeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_identity_id: UUID
    representative_type: RepresentativeTypeField
    position: Position = None
    valid_from: datetime | None = None
    source_document_reference: DocumentReference = None
    is_primary: bool | None = Field(default=None, description="Derivado del tipo; si se envía debe coincidir.")


class LegalRepresentativeSetPrimary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_identity_id: UUID
    position: Position = None
    valid_from: datetime | None = None
    source_document_reference: DocumentReference = None
    current_primary_version: int | None = Field(
        default=None, ge=1, description="Versión del PRIMARY vigente; se omite si no existe."
    )


class LegalRepresentativeUpdate(BaseModel):
    """Solo cargo y referencia documental; los demás campos responden `IMMUTABLE_FIELD`."""

    model_config = ConfigDict(extra="forbid")

    position: Position = None
    source_document_reference: DocumentReference = None
    version: int = Field(ge=1)
    person_identity_id: UUID | None = Field(default=None, description="Inmutable.")
    organization_identity_id: UUID | None = Field(default=None, description="Inmutable.")
    representative_type: str | None = Field(default=None, description="Inmutable.")


class LegalRepresentativeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_identity_id: UUID
    person_identity_id: UUID
    representative_type: RepresentativeTypeField
    position: str | None
    is_primary: bool
    is_active: bool
    valid_from: datetime
    valid_to: datetime | None
    source_document_reference: str | None
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
