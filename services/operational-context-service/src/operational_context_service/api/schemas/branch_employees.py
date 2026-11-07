"""Esquemas HTTP del listado de empleados por sucursal (FR-025a de la feature 005).

Los nombres y la identificación de la persona vienen de Party Identity en el
momento y no se persisten; son `null` si ese servicio no respondió.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from operational_context_service.application.branch_employees_service import (
    BranchEmployee,
    BranchEmployees,
)
from operational_context_service.domain.status import EntityStatus


class BranchEmployeeResponse(BaseModel):
    """Un empleado asignado a la sucursal."""

    application_user_id: UUID
    display_name: str
    reference_email: str | None
    keycloak_user_id: str
    person_identity_id: UUID
    identification_type: str | None
    identification_number: str | None
    first_name: str | None
    middle_name: str | None
    last_name: str | None
    second_last_name: str | None
    membership_status: EntityStatus
    user_branch_id: UUID
    user_branch_status: EntityStatus
    assigned_at: datetime
    allowed: bool
    reason: str | None

    @classmethod
    def of(cls, employee: BranchEmployee) -> BranchEmployeeResponse:
        user, assignment, person = employee.user, employee.assignment, employee.person

        return cls(
            application_user_id=user.id,
            display_name=user.display_name,
            reference_email=user.reference_email,
            keycloak_user_id=user.keycloak_user_id,
            person_identity_id=user.person_identity_id,
            identification_type=person.identification_type if person else None,
            identification_number=person.identification_number if person else None,
            first_name=person.first_name if person else None,
            middle_name=person.middle_name if person else None,
            last_name=person.last_name if person else None,
            second_last_name=person.second_last_name if person else None,
            membership_status=assignment.membership_status,
            user_branch_id=assignment.id,
            user_branch_status=assignment.status,
            assigned_at=assignment.assigned_at,
            allowed=employee.allowed,
            reason=employee.reason,
        )


class BranchEmployeesResponse(BaseModel):
    """Una sucursal con su código, su nombre y sus empleados."""

    branch_id: UUID
    code: str
    name: str
    status: EntityStatus
    employees: list[BranchEmployeeResponse]

    @classmethod
    def of(cls, group: BranchEmployees) -> BranchEmployeesResponse:
        return cls(
            branch_id=group.branch.id,
            code=group.branch.code,
            name=group.branch.name,
            status=group.branch.status,
            employees=[BranchEmployeeResponse.of(employee) for employee in group.employees],
        )
