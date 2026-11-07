"""Esquemas HTTP de los contratos de acceso operativo (`operational-access-provider.md`)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    """Sucursal asignada: acceso efectivo y sus datos (FR-070a)."""

    branch_id: UUID
    user_branch_status: EntityStatus
    branch_status: EntityStatus
    allowed: bool
    reason: str | None
    code: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line: str | None = None
    country_id: UUID | None = None
    administrative_division_id: UUID | None = None
    city_id: UUID | None = None
    postal_code: str | None = None
    timezone: str | None = Field(default=None, description="Zona horaria efectiva (la de la empresa si la sucursal no tiene).")

    @classmethod
    def of(cls, access) -> BranchAccessResponse:
        branch = access.branch
        details = {} if branch is None else {
            "code": branch.code, "name": branch.name, "email": branch.email, "phone": branch.phone,
            "address_line": branch.address_line, "country_id": branch.country_id,
            "administrative_division_id": branch.administrative_division_id, "city_id": branch.city_id,
            "postal_code": branch.postal_code, "timezone": branch.effective_timezone,
        }
        return cls(branch_id=access.branch_id, user_branch_status=access.user_branch_status,
                   branch_status=access.branch_status, allowed=access.allowed, reason=access.reason, **details)


class CompanyContextResponse(BaseModel):
    """Datos de la empresa de la membresía (FR-070a).

    `legal_name`, `trade_name`, `identification_type` e `identification_number` se leen de Party Identity
    en cada consulta (no se guardan); vienen en `null` si Party Identity no respondió.
    """

    id: UUID
    organization_identity_id: UUID
    legal_name: str | None
    trade_name: str | None
    identification_type: str | None
    identification_number: str | None
    email: str | None
    phone: str | None
    address_line: str | None
    country_id: UUID | None
    administrative_division_id: UUID | None
    city_id: UUID | None
    postal_code: str | None
    timezone: str
    default_currency: str
    status: EntityStatus

    @classmethod
    def of(cls, context) -> CompanyContextResponse:
        company, organization = context.company, context.organization
        return cls(
            id=company.id, organization_identity_id=company.organization_identity_id,
            legal_name=organization and organization.legal_name, trade_name=organization and organization.trade_name,
            identification_type=organization and organization.identification_type,
            identification_number=organization and organization.identification_number,
            email=company.email, phone=company.phone, address_line=company.address_line,
            country_id=company.country_id, administrative_division_id=company.administrative_division_id,
            city_id=company.city_id, postal_code=company.postal_code, timezone=company.timezone,
            default_currency=company.default_currency, status=company.status,
        )


class MembershipContextResponse(BaseModel):
    application_user_id: UUID
    company_id: UUID
    company_status: EntityStatus
    status: EntityStatus
    company: CompanyContextResponse | None = None
    branches: list[BranchAccessResponse]

    @classmethod
    def of(cls, membership) -> MembershipContextResponse:
        return cls(
            application_user_id=membership.application_user_id, company_id=membership.company_id,
            company_status=membership.company_status, status=membership.status,
            company=None if membership.company is None else CompanyContextResponse.of(membership.company),
            branches=[BranchAccessResponse.of(branch) for branch in membership.branches],
        )


class MeOperationalContextResponse(BaseModel):
    """Contexto operativo del usuario autenticado (FR-070)."""

    keycloak_user_id: str
    memberships: list[MembershipContextResponse]
