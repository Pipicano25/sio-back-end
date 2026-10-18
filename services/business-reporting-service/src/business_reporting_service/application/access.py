"""Autorización previa con Operational Context y el token del usuario (FR-023-11).

**Ninguna** llamada a Sales, Purchase, Inventory, CR ni PC sale antes de que esta función devuelva.

- Sin membresía `ACTIVE`, empresa inexistente o sin acceso → `404`, sin distinguir el caso.
- Sin `branch_id`: las sucursales `ACTIVE` de la empresa.
- Con `branch_id`: cada uno debe ser de la empresa (`404` si no); las inactivas se admiten si se nombran.
- No se exige asignación del usuario a la sucursal: con membresía y permiso de lectura, cualquier sucursal.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID

from business_reporting_service.application.exceptions import NotFoundError
from business_reporting_service.application.ports import BranchInfo, CompanyInfo, OperationalContextPort


@dataclass(frozen=True, slots=True)
class AuthorizedScope:
    company: CompanyInfo
    branches: tuple[BranchInfo, ...]
    explicit: bool
    """`True` si el usuario nombró las sucursales (filtro); `False` si es toda la empresa."""

    @property
    def branch_ids(self) -> list[UUID]:
        return [branch.id for branch in self.branches]

    def branch(self, branch_id: UUID) -> BranchInfo | None:
        return next((branch for branch in self.branches if branch.id == branch_id), None)


async def authorize(oc: OperationalContextPort, company_id: UUID, branch_ids: list[UUID] | None) -> AuthorizedScope:
    allowed, company, active = await asyncio.gather(
        oc.has_company_access(company_id), oc.company(company_id), oc.branches(company_id, status="ACTIVE")
    )
    if not allowed or company is None:
        raise NotFoundError()
    if not branch_ids:
        return AuthorizedScope(company, tuple(sorted(active, key=lambda b: (b.code, str(b.id)))), explicit=False)
    known = {branch.id: branch for branch in active}
    if any(branch_id not in known for branch_id in branch_ids):
        for branch in await oc.branches(company_id, status="INACTIVE"):
            known.setdefault(branch.id, branch)
    if any(branch_id not in known for branch_id in branch_ids):
        raise NotFoundError()
    return AuthorizedScope(company, tuple(known[b] for b in dict.fromkeys(branch_ids)), explicit=True)
