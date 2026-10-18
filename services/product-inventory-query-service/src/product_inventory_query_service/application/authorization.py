"""Autorización previa con Operational Context y el token del usuario (FR-022-11, FR-022-20 a 23; research R-02).

Tanda 0: la membresía y las sucursales `ACTIVE` se piden en paralelo. **Ninguna** llamada a CR, PC o Inventory sale
antes de que esta función devuelva: quien la llama solo consulta las demás dependencias con su resultado.

- Sin membresía `ACTIVE` o empresa inexistente → `404`, sin distinguir el caso.
- `scope = COMPANY` → las sucursales `ACTIVE` de la empresa.
- `branch_id` explícitos → cada uno debe ser de la empresa (`404` si no); las inactivas solo se admiten así.
- No se exige asignación del usuario a la sucursal: con membresía y permiso de lectura, cualquier sucursal de la
  empresa (A-08).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID

from product_inventory_query_service.application.exceptions import NotFoundError
from product_inventory_query_service.application.ports import BranchInfo, OperationalContextPort

NOT_FOUND_MESSAGE = "La empresa o la sucursal no existe o no tiene acceso."


@dataclass(frozen=True, slots=True)
class AuthorizedScope:
    company_id: UUID
    branches: tuple[BranchInfo, ...]

    @property
    def branch_ids(self) -> list[UUID]:
        return [branch.id for branch in self.branches]


async def authorize(oc: OperationalContextPort, company_id: UUID, branch_ids: list[UUID] | None) -> AuthorizedScope:
    """Verifica la membresía y resuelve el alcance de sucursales; `branch_ids = None` es `scope = COMPANY`."""
    allowed, active = await asyncio.gather(
        oc.has_company_access(company_id),
        oc.branches(company_id, status="ACTIVE"),
    )
    if not allowed:
        raise NotFoundError(NOT_FOUND_MESSAGE)

    if branch_ids is None:
        return AuthorizedScope(company_id, tuple(sorted(active, key=lambda b: str(b.id))))

    known = {branch.id: branch for branch in active}
    if any(branch_id not in known for branch_id in branch_ids):
        for branch in await oc.branches(company_id, status="INACTIVE"):
            known.setdefault(branch.id, branch)
    missing = [branch_id for branch_id in branch_ids if branch_id not in known]
    if missing:
        raise NotFoundError(NOT_FOUND_MESSAGE)
    return AuthorizedScope(company_id, tuple(known[branch_id] for branch_id in dict.fromkeys(branch_ids)))
