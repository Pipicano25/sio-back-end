"""Acceso a la empresa leído de la vista de contrato de Operational Context (spec 025, T030; D27).

`has_company_access` reproduce el adaptador HTTP sin llamar a `GET /operational-access`:

- sin el permiso de esa ruta en el token (`perm:operational-context:application_users:read`) → `False`, como hoy
  ante el `403` (FR-037);
- lee `contract.v1_operational_access` por `sub` y empresa: `True` solo si se permite y la empresa devuelta es nula
  o la pedida;
- la consulta es síncrona y se ejecuta en un hilo (`run_in_threadpool`) para no bloquear el bucle;
- cualquier error de base → `DependencyUnavailableError("operational-context")`, el mismo `503` de hoy.

`branches` (Historia 6) en lugar de `GET /companies/{c}/branches?status=` sobre `contract.v1_branches`, igual que en
Business Reporting (T074):

- sin `perm:operational-context:branches:read` → `[]` (el `403` de hoy);
- empresa visible solo con `platform:administer` o membresía `ACTIVE` del `sub` (sin `lookup`, como
  `BranchService._get_company`); si no, `[]` (el `404` de hoy);
- mismo orden (`created_at`, `id`) y el mismo tope de páginas que el cliente HTTP (`demasiadas_paginas`).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sio_auth import SioPermission
from sio_auth.permissions import has_permission
from sio_auth.tokens import TokenClaims
from sio_contract_read import contract_errors
from sio_contract_read.engine import read
from sio_contract_read.operational_access import ROUTE_PERMISSION, read_operational_access
from sqlalchemy import Engine
from starlette.concurrency import run_in_threadpool

from product_inventory_query_service.application.exceptions import OPERATIONAL_CONTEXT, DependencyUnavailableError
from product_inventory_query_service.application.ports import BranchInfo
from product_inventory_query_service.infrastructure.operational_context import (
    MAX_PAGES,
    PAGE_SIZE,
    HTTPOperationalContext,
)
from product_inventory_query_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
_REQUIRED = SioPermission(*ROUTE_PERMISSION)
_BRANCHES_READ = SioPermission("operational-context", "branches", "read")
_PLATFORM_ADMINISTER = SioPermission("operational-context", "platform", "administer")
OPERATION = "operational_access"
MAX_BRANCHES = MAX_PAGES * PAGE_SIZE
_MEMBER = (
    "EXISTS (SELECT 1 FROM contract.v1_operational_access a WHERE a.keycloak_user_id = :sub "
    "AND a.company_id = :company_id AND a.branch_id IS NULL "
    "AND a.denial_reason IS DISTINCT FROM 'USER_MEMBERSHIP_INACTIVE')"
)
_BRANCHES = "SELECT id, company_id, status FROM contract.v1_branches WHERE company_id = :company_id AND status = :status"
_BRANCHES_ORDER = " ORDER BY created_at, id LIMIT :limit"


def _unavailable(cause: str, operation: str = OPERATION) -> DependencyUnavailableError:
    return DependencyUnavailableError(OPERATIONAL_CONTEXT, operation, f"contract:{cause}")


class ContractOperationalContext:
    def __init__(self, *, engine: Engine, claims: TokenClaims | None, http: HTTPOperationalContext) -> None:
        self._engine = engine
        self._claims = claims
        self._http = http

    def _read(self, company_id: UUID):
        with contract_errors(_unavailable, dependency=OPERATIONAL_CONTEXT):
            return read_operational_access(self._engine, subject=self._claims.subject, company_id=company_id)

    async def has_company_access(self, company_id: UUID) -> bool:
        if self._claims is None or not has_permission(self._claims.permissions, _REQUIRED):
            logger.info("Operational Context negó el acceso a la empresa estado=%s", 403)
            return False
        access = await run_in_threadpool(self._read, company_id)
        return access.allowed and (access.company_id is None or access.company_id == company_id)

    def _allows(self, required: SioPermission) -> bool:
        return self._claims is not None and has_permission(self._claims.permissions, required)

    def _read_branches(self, company_id: UUID, status: str) -> list[BranchInfo]:
        operation = "branches"
        sql, params = _BRANCHES, {"company_id": company_id, "status": status, "limit": MAX_BRANCHES + 1}
        if not self._allows(_PLATFORM_ADMINISTER):
            sql, params = f"{sql} AND {_MEMBER}", {**params, "sub": self._claims.subject}
        with contract_errors(lambda cause: _unavailable(cause, operation), dependency=OPERATIONAL_CONTEXT):
            rows = read(self._engine, sql + _BRANCHES_ORDER, params)
        if len(rows) > MAX_BRANCHES:
            raise _unavailable("demasiadas_paginas", operation)
        found = []
        for row in rows:
            if not isinstance(row.get("status"), str) or row.get("id") is None:
                raise _unavailable("cuerpo_inesperado:branches", operation)
            found.append(BranchInfo(row["id"], row["company_id"], row["status"]))
        return found

    async def branches(self, company_id: UUID, *, status: str) -> list[BranchInfo]:
        if not self._allows(_BRANCHES_READ):
            logger.info("Operational Context negó la consulta de sucursales estado=%s", 403)
            return []
        return await run_in_threadpool(self._read_branches, company_id, status)
