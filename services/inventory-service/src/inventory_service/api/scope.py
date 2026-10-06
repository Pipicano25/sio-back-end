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
from inventory_service.application.exceptions import NotFoundError


def company_scope(company_id: UUID, request: Request) -> UUID:
    """Dependencia de las rutas de consulta: devuelve la empresa ya autorizada."""
    if technical_lookup(request):
        return company_id

    if not access_directory(request).is_member(company_id):
        raise NotFoundError()

    return company_id
