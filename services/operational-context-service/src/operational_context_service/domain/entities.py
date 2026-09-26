"""Entidades de dominio de la Fase A: empresa y sucursal.

No contienen datos cuya fuente de verdad sea otro servicio: la identidad legal
se referencia por `organization_identity_id` y la geografía por UUID
(Principio III, DS-01, DS-13).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from operational_context_service.domain.status import EntityStatus

LOCATION_FIELDS = ("country_id", "administrative_division_id", "city_id")


@dataclass(frozen=True, slots=True)
class Company:
    """Empresa cliente de la plataforma y su sede operativa principal."""

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


@dataclass(frozen=True, slots=True)
class Branch:
    """Sucursal de una empresa.

    `company_status` y `effective_timezone` se calculan en la consulta y no se
    persisten en `branches` (R-10, DS-08).
    """

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
