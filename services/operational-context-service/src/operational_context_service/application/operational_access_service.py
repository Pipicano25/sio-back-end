"""Contratos Provider de acceso operativo (US4; FR-070, FR-071, FR-075; DS-07, DS-08, C-14).

- `me`: membresías del `sub` del token y sus sucursales con acceso efectivo, con los
  datos de la empresa (nombre e identificación leídos de Party Identity, sin
  persistirlos) y de cada sucursal.
- `check`: acceso de un usuario a una empresa o sucursal, con causa estable.

Vía propia (token del usuario): una empresa o sucursal ajena **o inexistente**
responde `USER_NOT_MEMBER` sin revelar nada más. Vía técnica
(`platform:lookup` + `sub`): inexistente → `404`, y el permiso se evalúa con los
roles efectivos del usuario objetivo leídos de Keycloak (`sio_auth.evaluate_permission`);
nunca con los permisos del token técnico (R-11).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sio_auth import SioPermission, evaluate_permission

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.exceptions import DependencyUnavailableError, NotFoundError
from operational_context_service.application.ports import (
    ApplicationUserRepository,
    BranchRepository,
    CompanyRepository,
    IdentityAccountDirectory,
    MembershipLookup,
    OrganizationDirectory,
    OrganizationProfile,
    UserBranchRepository,
)
from operational_context_service.domain.entities import Branch, Company
from operational_context_service.domain.access import (
    AccessDenialReason,
    AccessFacts,
    evaluate_own_access,
    evaluate_technical_access,
)
from operational_context_service.domain.errors import DomainValidationError, OperationalContextError

logger = logging.getLogger(__name__)


def _with_organization(context: MembershipContext, profile: OrganizationProfile | None) -> MembershipContext:
    company = CompanyContext(context.company.company, profile)
    return MembershipContext(
        application_user_id=context.application_user_id,
        company_id=context.company_id,
        company_status=context.company_status,
        status=context.status,
        branches=context.branches,
        company=company,
    )


class LookupCapabilityRequiredError(OperationalContextError):
    """Consultar el acceso de otro `sub` exige `platform:lookup` (FR-045)."""

    code = "FORBIDDEN"
    title = "Acceso denegado"
    default_message = (
        "Consultar el acceso de otro usuario requiere el permiso "
        "perm:operational-context:platform:lookup."
    )


@dataclass(frozen=True, slots=True)
class AccessResult:
    """Resultado funcional de `operational-access` (siempre `200`)."""

    allowed: bool
    reason: str | None
    keycloak_user_id: str
    company_id: UUID | None
    branch_id: UUID | None
    application_user_id: UUID | None
    permission: str | None


@dataclass(frozen=True, slots=True)
class BranchAccess:
    branch_id: UUID
    user_branch_status: str
    branch_status: str
    allowed: bool
    reason: str | None
    branch: Branch | None = None


@dataclass(frozen=True, slots=True)
class CompanyContext:
    """Empresa de una membresía: datos propios y, si Party Identity respondió, su nombre."""

    company: Company
    organization: OrganizationProfile | None


@dataclass(frozen=True, slots=True)
class MembershipContext:
    application_user_id: UUID
    company_id: UUID
    company_status: str
    status: str
    branches: list[BranchAccess]
    company: CompanyContext | None = None


def parse_permission(value: str | None) -> SioPermission | None:
    """`perm:{servicio}:{recurso}:{accion}` concreto (sin `all`) o `None`.

    Raises:
        DomainValidationError: Formato inválido o con `all` (`422`).
    """
    if value is None:
        return None

    parts = value.strip().split(":")

    if len(parts) != 4 or parts[0] != "perm":
        raise DomainValidationError(
            "El permiso debe tener el formato perm:{servicio}:{recurso}:{accion}.",
            field="permission",
        )

    try:
        return SioPermission(parts[1], parts[2], parts[3])
    except ValueError:
        raise DomainValidationError(
            "El permiso debe ser concreto: sin 'all' y con segmentos válidos.",
            field="permission",
        ) from None


class OperationalAccessService:
    """Evalúa el acceso operativo efectivo; nunca lo persiste (DS-07)."""

    def __init__(
        self,
        companies: CompanyRepository,
        branches: BranchRepository,
        user_branches: UserBranchRepository,
        memberships: MembershipLookup,
        accounts: IdentityAccountDirectory,
        users: ApplicationUserRepository,
        organizations: OrganizationDirectory | None = None,
    ) -> None:
        self.organizations = organizations
        self.users = users
        self.companies = companies
        self.branches = branches
        self.user_branches = user_branches
        self.memberships = memberships
        self.accounts = accounts

    def check(
        self,
        scope: AccessScope,
        *,
        company_id: UUID | None,
        branch_id: UUID | None,
        permission: str | None,
        keycloak_user_id: str | None,
    ) -> AccessResult:
        if (company_id is None) == (branch_id is None):
            raise DomainValidationError(
                "Indique exactamente uno de branch_id o company_id.",
                field="branch_id",
            )

        required = parse_permission(permission)
        technical = keycloak_user_id is not None

        if technical and not scope.can_lookup:
            raise LookupCapabilityRequiredError

        subject = keycloak_user_id.strip() if technical else scope.subject

        branch = None
        if branch_id is not None:
            branch = self.branches.get_by_id(branch_id)
            self.branches.end_read()
            company_id_resolved = branch.company_id if branch is not None else None
        else:
            company_id_resolved = company_id

        company = None
        if company_id_resolved is not None:
            company = self.companies.get_by_id(company_id_resolved)
            self.companies.end_read()

        if technical and (company is None or (branch_id is not None and branch is None)):
            raise NotFoundError("La empresa o sucursal indicada no existe.")

        membership = None
        if company is not None:
            membership = self.memberships.find_membership(company.id, subject)

        user_branch_status = None
        if branch is not None and membership is not None:
            pair = self.user_branches.find_pair(membership.id, branch.id)
            self.user_branches.end_read()
            user_branch_status = None if pair is None else pair.status

        permission_granted = None
        if required is not None:
            if technical:
                def permission_granted() -> bool:
                    return evaluate_permission(self.accounts.get_permission_roles(subject), required)
            else:
                def permission_granted() -> bool:
                    return scope.has_permission(required)

        facts = AccessFacts(
            company_status=None if company is None else company.status,
            branch_requested=branch_id is not None,
            branch_status=None if branch is None else branch.status,
            membership_status=None if membership is None else membership.status,
            user_branch_status=user_branch_status,
            permission_granted=permission_granted,
        )
        reason = evaluate_technical_access(facts) if technical else evaluate_own_access(facts)

        if reason is AccessDenialReason.USER_NOT_MEMBER and not technical:
            # C-14: no se revela si la empresa o sucursal existe ni su estado.
            return AccessResult(
                allowed=False,
                reason=reason.value,
                keycloak_user_id=subject,
                company_id=company_id,
                branch_id=branch_id,
                application_user_id=None,
                permission=permission,
            )

        return AccessResult(
            allowed=reason is None,
            reason=None if reason is None else reason.value,
            keycloak_user_id=subject,
            company_id=None if company is None else company.id,
            branch_id=branch_id,
            application_user_id=None if membership is None else membership.id,
            permission=permission,
        )

    def me(self, scope: AccessScope) -> list[MembershipContext]:
        """Membresías (activas e inactivas) del `sub` del token y sus sucursales (FR-070).

        No evalúa permisos concretos. Lee la base y la cierra antes de consultar el
        nombre de cada empresa en Party Identity con el token del usuario (R-09); si
        Party Identity no responde o lo deniega, esos campos quedan en `null` y el
        contexto se devuelve igual (FR-070a).
        """
        users = self.users.list_by_subject(scope.subject)
        self.users.end_read()
        contexts: list[MembershipContext] = []
        companies: dict[UUID, Company] = {}

        for user in users:
            assignments = self.user_branches.list_all_for_user(user.id)
            self.user_branches.end_read()
            company = companies.get(user.company_id) or self.companies.get_by_id(user.company_id)
            if company is not None:
                companies[company.id] = company
            branches = []
            for assignment in assignments:
                reason = evaluate_own_access(
                    AccessFacts(
                        company_status=user.company_status,
                        branch_requested=True,
                        branch_status=assignment.branch_status,
                        membership_status=user.status,
                        user_branch_status=assignment.status,
                    )
                )
                branches.append(
                    BranchAccess(
                        branch_id=assignment.branch_id,
                        user_branch_status=assignment.status,
                        branch_status=assignment.branch_status,
                        allowed=reason is None,
                        reason=None if reason is None else reason.value,
                        branch=self.branches.get_by_id(assignment.branch_id),
                    )
                )
            contexts.append(
                MembershipContext(
                    application_user_id=user.id,
                    company_id=user.company_id,
                    company_status=user.company_status,
                    status=user.status,
                    branches=branches,
                    company=None if company is None else CompanyContext(company, None),
                )
            )

        self.companies.end_read()
        self.branches.end_read()
        profiles = self._organization_profiles(companies.values())

        return [
            context
            if context.company is None
            else _with_organization(context, profiles.get(context.company.company.organization_identity_id))
            for context in contexts
        ]

    def _organization_profiles(self, companies) -> dict[UUID, OrganizationProfile]:
        """Nombre e identificación de cada empresa; lo que no se pueda leer se omite."""
        profiles: dict[UUID, OrganizationProfile] = {}
        if self.organizations is None:
            return profiles
        for organization_id in {company.organization_identity_id for company in companies}:
            try:
                profile = self.organizations.get_organization_profile(organization_id)
            except DependencyUnavailableError:
                logger.warning("contexto_operativo_sin_nombre_empresa organization_identity_id=%s", organization_id)
                continue
            if profile is not None:
                profiles[organization_id] = profile
        return profiles
