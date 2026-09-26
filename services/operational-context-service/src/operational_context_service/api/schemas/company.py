"""Esquemas HTTP de empresas (`contracts/rest-api.md`, sección 1).

La empresa no recibe ni devuelve razón social, nombre comercial ni
identificación: se consultan en Party Identity con `organization_identity_id`
(DS-01, DS-13).
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from operational_context_service.api.schemas.common import (
    AddressLine,
    Latitude,
    Longitude,
    OptionalEmail,
    Phone,
    PostalCode,
    StrictModel,
    TimezoneText,
    Version,
)
from operational_context_service.domain.currency import DEFAULT_CURRENCY
from operational_context_service.domain.status import EntityStatus
from operational_context_service.domain.timezone import DEFAULT_TIMEZONE


class _CompanyFields(StrictModel):
    organization_identity_id: UUID
    email: OptionalEmail = None
    phone: Phone = None
    address_line: AddressLine = None
    country_id: UUID | None = None
    administrative_division_id: UUID | None = None
    city_id: UUID | None = None
    postal_code: PostalCode = None
    latitude: Latitude = None
    longitude: Longitude = None


class CompanyCreate(_CompanyFields):
    """Alta de empresa; zona horaria y moneda tienen valor por defecto."""

    timezone: TimezoneText = DEFAULT_TIMEZONE
    default_currency: str = DEFAULT_CURRENCY


class CompanyUpdate(_CompanyFields):
    """`PUT` de empresa: reemplazo completo con versión esperada."""

    timezone: TimezoneText
    default_currency: str
    version: Version


class CompanyResponse(BaseModel):
    """Representación de una empresa."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_identity_id: UUID
    email: str | None
    phone: str | None
    address_line: str | None
    country_id: UUID | None
    administrative_division_id: UUID | None
    city_id: UUID | None
    postal_code: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    timezone: str
    default_currency: str
    status: EntityStatus
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
