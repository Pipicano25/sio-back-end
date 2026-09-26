"""Entidad de dominio para identidades globales de organizaciones."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from party_identity_service.domain.person_identity import IdentityStatus


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
    status: IdentityStatus
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
