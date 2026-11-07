"""Empleados de una empresa agrupados por sucursal (FR-025a de la feature 005).

Solo lectura. Une sucursales, asignaciones y membresías de Operational Context
y completa el nombre y la identificación de cada persona con Party Identity,
consultados en el momento con el token del usuario y nunca persistidos (RC-13).
Si Party Identity no responde o niega la lectura, esos campos quedan en `null`
y el listado responde igual. La lectura de la base se cierra antes de cualquier
llamada HTTP (R-09).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.exceptions import DependencyUnavailableError, NotFoundError
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.ports import (
    ApplicationUserRepository,
    BranchFilters,
    BranchRepository,
    CompanyRepository,
    PersonDirectory,
    PersonProfile,
    UserBranchRepository,
)
from operational_context_service.application.user_branch_service import assignment_access
from operational_context_service.domain.entities import ApplicationUser, Branch, UserBranch
from operational_context_service.domain.status import EntityStatus
from operational_context_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

COMPANY_NOT_FOUND_MESSAGE = "La empresa solicitada no existe."
BRANCH_NOT_FOUND_MESSAGE = "La sucursal solicitada no existe."


@dataclass(frozen=True, slots=True)
class BranchEmployee:
    """Un empleado asignado a una sucursal, con su persona si se pudo consultar."""

    assignment: UserBranch
    user: ApplicationUser
    person: PersonProfile | None
    allowed: bool
    reason: str | None


@dataclass(frozen=True, slots=True)
class BranchEmployees:
    """Una sucursal con sus empleados asignados."""

    branch: Branch
    employees: list[BranchEmployee]


class BranchEmployeesService:
    """Arma el listado de empleados por sucursal de una empresa visible."""

    def __init__(
        self,
        companies: CompanyRepository,
        branches: BranchRepository,
        user_branches: UserBranchRepository,
        users: ApplicationUserRepository,
        persons: PersonDirectory,
    ) -> None:
        self.companies = companies
        self.branches = branches
        self.user_branches = user_branches
        self.users = users
        self.persons = persons

    def list(
        self,
        scope: AccessScope,
        company_id: UUID,
        *,
        branch_id: UUID | None,
        branch_status: EntityStatus,
        assignment_status: EntityStatus,
        search: str | None,
        page: int,
        page_size: int,
    ) -> PageResult[BranchEmployees]:
        """Página de sucursales con sus empleados; `404` si la empresa o la sucursal no son visibles."""
        company = self.companies.get_by_id(company_id)
        self.companies.end_read()

        if company is None:
            raise NotFoundError(COMPANY_NOT_FOUND_MESSAGE)

        scope.ensure_company_visible(company_id)
        branches = self._branches(company_id, branch_id, branch_status, search, page=page, page_size=page_size)
        assignments = self.user_branches.list_for_branches(
            [branch.id for branch in branches.items],
            status=assignment_status,
        )
        users = {
            user.id: user
            for user in self.users.list_by_ids({assignment.application_user_id for assignment in assignments})
        }
        self.branches.end_read()
        self.user_branches.end_read()
        self.users.end_read()

        persons = self._person_profiles({user.person_identity_id for user in users.values()})
        by_branch: dict[UUID, list[BranchEmployee]] = {branch.id: [] for branch in branches.items}

        for assignment in assignments:
            user = users.get(assignment.application_user_id)

            if user is None:
                continue

            allowed, reason = assignment_access(assignment)
            by_branch[assignment.branch_id].append(
                BranchEmployee(
                    assignment=assignment,
                    user=user,
                    person=persons.get(user.person_identity_id),
                    allowed=allowed,
                    reason=reason,
                )
            )

        return PageResult(
            items=[BranchEmployees(branch=branch, employees=by_branch[branch.id]) for branch in branches.items],
            page=branches.page,
            page_size=branches.page_size,
            total_records=branches.total_records,
        )

    def _branches(
        self,
        company_id: UUID,
        branch_id: UUID | None,
        status: EntityStatus,
        search: str | None,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[Branch]:
        """Una sola sucursal (en cualquier estado) si se pidió por id; si no, la página filtrada."""
        if branch_id is None:
            return self.branches.list_by_company(
                company_id,
                BranchFilters(status=status, search=search),
                page=page,
                page_size=page_size,
            )

        branch = self.branches.get_by_id(branch_id)

        if branch is None or branch.company_id != company_id:
            self.branches.end_read()
            raise NotFoundError(BRANCH_NOT_FOUND_MESSAGE)

        return PageResult(items=[branch], page=1, page_size=page_size, total_records=1)

    def _person_profiles(self, person_ids: set[UUID]) -> dict[UUID, PersonProfile]:
        """Perfiles de Party Identity; ante la primera falla se deja de consultar (campos en `null`)."""
        profiles: dict[UUID, PersonProfile] = {}

        for person_id in sorted(person_ids, key=str):
            try:
                profile = self.persons.get_person_profile(person_id)
            except DependencyUnavailableError:
                logger.warning("empleados_por_sucursal_sin_datos_de_persona person_identity_id=%s", person_id)
                break

            if profile is not None:
                profiles[person_id] = profile

        return profiles
