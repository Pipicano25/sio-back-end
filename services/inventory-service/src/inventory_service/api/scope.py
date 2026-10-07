"""Alcance de las consultas por empresa (DS-12, DS-16; research.md R-08; RC-06).

- Cuenta de servicio con el permiso de lectura **y** `perm:inventory:platform:lookup`
  → sin consultar Operational Context.
- Cualquier otro token (incluida una cuenta de servicio sin `platform:lookup`) →
  `operational-access?company_id=` con **su** token: miembro `ACTIVE` (o empresa
  inactiva) → permitido; si no → `404` sin revelar existencia. No se exige
  asignación a la sucursal consultada.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Request

from inventory_service.api.dependencies import access_directory
from inventory_service.api.identity import technical_lookup
from inventory_service.application.branch_access import OperatorAccess, require_branch_access, require_membership
from inventory_service.application.exceptions import NotFoundError


def company_scope(company_id: UUID, request: Request) -> UUID:
    """Dependencia de las rutas de consulta: devuelve la empresa ya autorizada."""
    if technical_lookup(request):
        return company_id

    if not access_directory(request).is_member(company_id):
        raise NotFoundError()

    return company_id


def branch_operator(request: Request, company_id: UUID, branch_id: UUID) -> OperatorAccess:
    """Usuario humano con membresía y asignación `ACTIVE` a la sucursal (013 R-09, DS-14)."""
    return require_branch_access(access_directory(request), company_id, branch_id)


def company_operator(request: Request, company_id: UUID) -> OperatorAccess:
    """Usuario humano miembro de la empresa (escritura de políticas)."""
    return require_membership(access_directory(request), company_id)
