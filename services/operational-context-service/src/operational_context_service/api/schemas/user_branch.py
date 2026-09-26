"""Esquemas HTTP de asignaciones usuario–sucursal (`contracts/rest-api.md` de la feature 005, §2)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from operational_context_service.api.schemas.common import StrictModel
from operational_context_service.domain.status import EntityStatus


class UserBranchCreate(StrictModel):
    """Alta: solo la sucursal; el usuario viene de la ruta y el autor del token."""

    branch_id: UUID


class OperationalAccessSummary(BaseModel):
    """Acceso operativo efectivo de la asignación, sin evaluar permisos (R-10)."""

    allowed: bool
    reason: str | None


class UserBranchResponse(BaseModel):
    """Representación de una asignación usuario–sucursal."""

    model_config = ConfigDict(from_attributes=True)

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
    operational_access: OperationalAccessSummary
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
