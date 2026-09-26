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


# ---------------------------------------------------------------------------
# Fase B: usuarios operativos, asignaciones y asesores (data-model de la
# feature 005). Solo guardan UUID y `sub`: nombres e identificación de la
# persona pertenecen a Party Identity (Principio III, FR-065).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApplicationUser:
    """Membresía de una persona humana en una empresa (DS-01, DS-16).

    `company_status` se calcula en la consulta y no se persiste.
    """

    id: UUID
    company_id: UUID
    company_status: EntityStatus
    keycloak_user_id: str
    person_identity_id: UUID
    display_name: str
    reference_email: str | None
    status: EntityStatus
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class UserBranch:
    """Asignación de un usuario operativo a una sucursal de su misma empresa.

    `membership_status`, `branch_status` y `company_status` se calculan en la
    consulta (JOIN) y no se persisten.
    """

    id: UUID
    application_user_id: UUID
    branch_id: UUID
    company_id: UUID
    status: EntityStatus
    assigned_at: datetime
    assigned_by: str
    deactivated_at: datetime | None
    membership_status: EntityStatus
    branch_status: EntityStatus
    company_status: EntityStatus
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AdvisorAssignment:
    """Asignación de asesor de una empresa con vigencia (DS-13)."""

    id: UUID
    company_id: UUID
    person_identity_id: UUID
    is_primary: bool
    status: EntityStatus
    valid_from: datetime
    valid_to: datetime | None
    assigned_by: str
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
