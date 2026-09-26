"""Casos de uso de asignaciones usuario–sucursal (US2 y US6 de la feature 005).

Sin proveedores externos. El autor (`assigned_by`) es siempre el `sub` del
token (DS-10). La sucursal debe ser de la misma empresa que la membresía
(FR-020, RC-06) y membresía, sucursal y empresa deben estar `ACTIVE` para
crear o reactivar (RN-10).
"""

from __future__ import annotations

import logging
from uuid import UUID

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.exceptions import (
    BranchCompanyMismatchError,
    BranchInactiveError,
    CompanyInactiveError,
    DuplicateUserBranchError,
    InvalidStatusTransitionError,
    MembershipInactiveError,
    NotFoundError,
    VersionConflictError,
)
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.ports import (
    ApplicationUserRepository,
    BranchRepository,
    UserBranchRepository,
)
from operational_context_service.domain.access import AccessFacts, evaluate_technical_access
from operational_context_service.domain.entities import UserBranch
from operational_context_service.domain.status import ACTIVE, INACTIVE, EntityStatus
from operational_context_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

NOT_FOUND_MESSAGE = "La asignación solicitada no existe."
USER_NOT_FOUND_MESSAGE = "El usuario operativo solicitado no existe."
BRANCH_NOT_FOUND_MESSAGE = "La sucursal solicitada no existe."


def assignment_access(user_branch: UserBranch) -> tuple[bool, str | None]:
    """Acceso operativo efectivo de una asignación, sin permiso concreto (DS-07)."""
    reason = evaluate_technical_access(
        AccessFacts(
            company_status=user_branch.company_status,
            branch_requested=True,
            branch_status=user_branch.branch_status,
            membership_status=user_branch.membership_status,
            user_branch_status=user_branch.status,
        )
    )

    return reason is None, None if reason is None else reason.value


class UserBranchService:
    """Orquesta los casos de uso de asignaciones."""

    def __init__(
        self,
        repository: UserBranchRepository,
        users: ApplicationUserRepository,
        branches: BranchRepository,
    ) -> None:
        self.repository = repository
        self.users = users
        self.branches = branches

    # ------------------------------------------------------------------ consultas

    def get(self, scope: AccessScope, user_branch_id: UUID) -> UserBranch:
        user_branch = self.repository.get_by_id(user_branch_id)
        self.repository.end_read()

        if user_branch is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)

        scope.ensure_company_visible(user_branch.company_id, not_found_message=NOT_FOUND_MESSAGE)

        return user_branch

    def list_by_user(
        self,
        scope: AccessScope,
        application_user_id: UUID,
        status: EntityStatus,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[UserBranch]:
        self._visible_user(scope, application_user_id)
        result = self.repository.list_by(
            application_user_id=application_user_id,
            status=status,
            page=page,
            page_size=page_size,
        )
        self.repository.end_read()

        return result

    def list_by_branch(
        self,
        scope: AccessScope,
        branch_id: UUID,
        status: EntityStatus,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[UserBranch]:
        self._visible_branch(scope, branch_id)
        result = self.repository.list_by(branch_id=branch_id, status=status, page=page, page_size=page_size)
        self.repository.end_read()

        return result

    # ------------------------------------------------------------------ escritura

    def create(
        self,
        scope: AccessScope,
        application_user_id: UUID,
        branch_id: UUID,
        *,
        actor_id: str,
    ) -> UserBranch:
        """Asigna una sucursal de la misma empresa (FR-020 a FR-022)."""
        user = self._visible_user(scope, application_user_id)
        branch = self.branches.get_by_id(branch_id)
        self.branches.end_read()

        if branch is None or not scope.is_company_visible(branch.company_id):
            raise NotFoundError(BRANCH_NOT_FOUND_MESSAGE)

        if branch.company_id != user.company_id:
            raise BranchCompanyMismatchError(field="branch_id")

        if user.status != ACTIVE:
            raise MembershipInactiveError(field="application_user_id")

        if user.company_status != ACTIVE:
            raise CompanyInactiveError(
                "La empresa está inactiva: no se pueden crear ni reactivar asignaciones."
            )

        if branch.status != ACTIVE:
            raise BranchInactiveError(field="branch_id")

        if self.repository.find_pair(application_user_id, branch_id) is not None:
            self.repository.end_read()
            raise DuplicateUserBranchError(field="branch_id")

        self.repository.end_read()

        user_branch = self.repository.create(
            application_user_id=application_user_id,
            branch_id=branch_id,
            company_id=user.company_id,
            actor_id=actor_id,
        )
        logger.info(
            "Sucursal asignada id=%s usuario=%s sucursal=%s",
            user_branch.id,
            application_user_id,
            branch_id,
        )

        return user_branch

    def deactivate(
        self,
        scope: AccessScope,
        user_branch_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> UserBranch:
        """Retira la asignación sin eliminarla (FR-023, D7)."""
        current = self.get(scope, user_branch_id)

        if current.version != expected_version:
            raise VersionConflictError

        if current.status == INACTIVE:
            raise InvalidStatusTransitionError("La asignación ya se encuentra en estado INACTIVE.")

        return self.repository.deactivate(user_branch_id, expected_version=expected_version, actor_id=actor_id)

    def reactivate(
        self,
        scope: AccessScope,
        user_branch_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> UserBranch:
        """Reactiva si membresía, sucursal y empresa siguen `ACTIVE` (FR-023, RN-10)."""
        current = self.get(scope, user_branch_id)

        if current.version != expected_version:
            raise VersionConflictError

        if current.status == ACTIVE:
            raise InvalidStatusTransitionError("La asignación ya se encuentra en estado ACTIVE.")

        return self.repository.reactivate(user_branch_id, expected_version=expected_version, actor_id=actor_id)

    # ------------------------------------------------------------------ apoyo

    def _visible_user(self, scope: AccessScope, application_user_id: UUID):
        user = self.users.get_by_id(application_user_id)
        self.users.end_read()

        if user is None:
            raise NotFoundError(USER_NOT_FOUND_MESSAGE)

        scope.ensure_company_visible(user.company_id, not_found_message=USER_NOT_FOUND_MESSAGE)

        return user

    def _visible_branch(self, scope: AccessScope, branch_id: UUID):
        branch = self.branches.get_by_id(branch_id)
        self.branches.end_read()

        if branch is None:
            raise NotFoundError(BRANCH_NOT_FOUND_MESSAGE)

        scope.ensure_company_visible(branch.company_id, not_found_message=BRANCH_NOT_FOUND_MESSAGE)

        return branch
