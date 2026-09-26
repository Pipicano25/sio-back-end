"""Esquemas HTTP de asesores (`contracts/rest-api.md` de la feature 005, §3).

No se reciben ni devuelven nombres ni datos de contacto del asesor: pertenecen
a Party Identity (FR-057).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from operational_context_service.api.schemas.common import StrictModel, Version
from operational_context_service.domain.status import EntityStatus


class AdvisorAssignmentCreate(StrictModel):
    person_identity_id: UUID
    is_primary: bool = True
    valid_from: datetime | None = None


class AdvisorCloseRequest(StrictModel):
    version: Version
    valid_to: datetime | None = None


class ChangePrimaryRequest(StrictModel):
    current_assignment_id: UUID
    version: Version
    person_identity_id: UUID
    effective_at: datetime | None = None


class AdvisorAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ChangePrimaryResponse(BaseModel):
    """Resultado atómico: la asignación cerrada y la nueva vigente."""

    closed: AdvisorAssignmentResponse
    created: AdvisorAssignmentResponse
