"""Acceso a la empresa leído de la vista de contrato de Operational Context (spec 025, T031; D27).

`has_company_access` reproduce el adaptador HTTP sin llamar a `GET /operational-access`:

- sin el permiso de esa ruta en el token (`perm:operational-context:application_users:read`) → `False`, como hoy
  ante el `403` (FR-037);
- lee `contract.v1_operational_access` por `sub` y empresa: `True` solo si se permite y la empresa devuelta es nula
  o la pedida;
- la consulta es síncrona y se ejecuta en un hilo (`run_in_threadpool`) para no bloquear el bucle;
- cualquier error de base → `DependencyUnavailableError("operational-context")`, el mismo `503` de hoy.

`company` y `branches` siguen por HTTP en esta fase (Historia 6).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sio_auth import SioPermission
from sio_auth.permissions import has_permission
from sio_auth.tokens import TokenClaims
from sio_contract_read import contract_errors
from sio_contract_read.operational_access import ROUTE_PERMISSION, read_operational_access
from sqlalchemy import Engine
from starlette.concurrency import run_in_threadpool

from business_reporting_service.application.exceptions import OPERATIONAL_CONTEXT, DependencyUnavailableError
from business_reporting_service.application.ports import BranchInfo, CompanyInfo
from business_reporting_service.infrastructure.operational_context import HTTPOperationalContext
from business_reporting_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
_REQUIRED = SioPermission(*ROUTE_PERMISSION)
OPERATION = "operational_access"


def _unavailable(cause: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(OPERATIONAL_CONTEXT, OPERATION, f"contract:{cause}")


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

    async def company(self, company_id: UUID) -> CompanyInfo | None:
        return await self._http.company(company_id)

    async def branches(self, company_id: UUID, *, status: str) -> list[BranchInfo]:
        return await self._http.branches(company_id, status=status)
