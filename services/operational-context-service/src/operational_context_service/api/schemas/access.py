"""Esquemas HTTP de los contratos de acceso operativo (`operational-access-provider.md`)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from operational_context_service.domain.status import EntityStatus


class OperationalAccessResponse(BaseModel):
    """Resultado funcional de `GET /operational-access` (siempre `200`, DS-08)."""

    model_config = ConfigDict(from_attributes=True)

    allowed: bool
    reason: str | None
    keycloak_user_id: str
    company_id: UUID | None
    branch_id: UUID | None
    application_user_id: UUID | None
    permission: str | None


class BranchAccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    branch_id: UUID
    user_branch_status: EntityStatus
    branch_status: EntityStatus
    allowed: bool
    reason: str | None


class MembershipContextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_user_id: UUID
    company_id: UUID
    company_status: EntityStatus
    status: EntityStatus
    branches: list[BranchAccessResponse]


class MeOperationalContextResponse(BaseModel):
    """Contexto operativo del usuario autenticado (FR-070)."""

    keycloak_user_id: str
    memberships: list[MembershipContextResponse]
