"""Schemas HTTP de sectores y asignaciones (contracts/rest-api.md §3 y §4)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from party_identity_service.domain.business_sector import SectorStatus

SystemCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
SectorCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
SectorName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)]


class BusinessSectorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification_system: SystemCode
    code: SectorCode
    name: SectorName
    description: str | None = None
    parent_sector_id: UUID | None = None


class BusinessSectorUpdate(BaseModel):
    """`classification_system` y `code` solo se aceptan para responder `IMMUTABLE_FIELD`."""

    model_config = ConfigDict(extra="forbid")

    name: SectorName
    description: str | None = None
    parent_sector_id: UUID | None = None
    version: int = Field(ge=1)
    classification_system: str | None = Field(default=None, description="Inmutable.")
    code: str | None = Field(default=None, description="Inmutable.")


class BusinessSectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parent_sector_id: UUID | None
    classification_system: str
    code: str
    name: str
    description: str | None
    status: SectorStatus
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class OrganizationBusinessSectorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    global_business_sector_id: UUID
    is_primary: bool = False
    valid_from: datetime | None = None


class OrganizationBusinessSectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_identity_id: UUID
    global_business_sector_id: UUID
    is_primary: bool
    is_active: bool
    valid_from: datetime
    valid_to: datetime | None
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
