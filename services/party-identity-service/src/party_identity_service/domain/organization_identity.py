"""Entidad de dominio para identidades globales de organizaciones."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


OrganizationIdentificationType = str


@dataclass(frozen=True, slots=True)
class OrganizationIdentity:
    """Representa la identidad legal global de una organización."""

    id: UUID
    country_id: UUID
    identification_type: OrganizationIdentificationType
    identification_number: str
    legal_name: str
    trade_name: str | None
    organization_type: str | None
    registration_status: str | None
    website: str | None
    version: int
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
