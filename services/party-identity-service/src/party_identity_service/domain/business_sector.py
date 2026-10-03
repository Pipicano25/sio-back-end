"""Entidades de dominio de sectores económicos (Fase B)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

SectorStatus = Literal["ACTIVE", "INACTIVE"]

CIIU_CLASSIFICATION_SYSTEM = "CIIU_REV5_AC"
"""Identificador estable de la CIIU Rev. 5 A.C. del DANE (DS-10; Resolución DANE 992 de 2026)."""


def normalize_code(value: str) -> str:
    """Normaliza `classification_system` y `code`: mayúsculas sin espacios exteriores."""
    return value.strip().upper()


@dataclass(frozen=True, slots=True)
class BusinessSector:
    """Sector económico global y jerárquico (estándar 4.7)."""

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


@dataclass(frozen=True, slots=True)
class OrganizationBusinessSector:
    """Asignación de un sector a una organización con vigencia `[valid_from, valid_to)`."""

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
