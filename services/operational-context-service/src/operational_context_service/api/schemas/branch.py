"""Esquemas HTTP de sucursales (`contracts/rest-api.md`, sección 2).

`company_id` no se acepta en el cuerpo: en el alta viene de la ruta y después
es inmutable (FR-020, FR-022). Un `company_id` en el cuerpo → `422`.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from operational_context_service.api.schemas.common import (
    AddressLine,
    Latitude,
    Longitude,
    OptionalEmail,
    OptionalTimezoneText,
    Phone,
    PostalCode,
    StrictModel,
    Version,
)
from operational_context_service.domain.status import EntityStatus


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


BranchName = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=160)]


class BranchCreate(StrictModel):
    """Alta de sucursal; `timezone` nulo = hereda la de la empresa (DS-08)."""

    code: str
    name: BranchName
    email: OptionalEmail = None
    phone: Phone = None
    address_line: AddressLine = None
    country_id: UUID | None = None
    administrative_division_id: UUID | None = None
    city_id: UUID | None = None
    postal_code: PostalCode = None
    latitude: Latitude = None
    longitude: Longitude = None
    timezone: OptionalTimezoneText = None


class BranchUpdate(BranchCreate):
    """`PUT` de sucursal: reemplazo completo con versión esperada."""

    version: Version


class BranchResponse(BaseModel):
    """Representación de una sucursal con sus campos calculados (R-10)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    company_status: EntityStatus
    code: str
    name: str
    email: str | None
    phone: str | None
    address_line: str | None
    country_id: UUID | None
    administrative_division_id: UUID | None
    city_id: UUID | None
    postal_code: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    timezone: str | None
    effective_timezone: str
    status: EntityStatus
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
