"""Operational Context leído de sus vistas de contrato con el permiso del usuario (spec 025, T031 y T074; D27).

Implementa el mismo puerto que `HTTPOperationalContext` sin llamar a Operational Context:

- `has_company_access` (T031) en lugar de `GET /operational-access`: sin el permiso de esa ruta en el token
  (`perm:operational-context:application_users:read`) → `False`, como hoy ante el `403` (FR-037); lee
  `contract.v1_operational_access` por `sub` y empresa: `True` solo si se permite y la empresa devuelta es nula o la
  pedida.
- `company` (T074) en lugar de `GET /companies/{c}` sobre `contract.v1_companies`: sin
  `perm:operational-context:companies:read` → `None` (el `403` de hoy); la empresa solo es visible, como en
  `AccessScope.ensure_company_visible(lookup_read=True)`, con `platform:administer`, `platform:lookup` o una
  membresía `ACTIVE` del `sub`; si no, `None` (el `404` de hoy, que no distingue).
- `branches` (T074) en lugar de `GET /companies/{c}/branches?status=` sobre `contract.v1_branches`: sin
  `perm:operational-context:branches:read` → `[]` (el `403` de hoy); empresa visible solo con `platform:administer` o
  membresía `ACTIVE` (sin `lookup`, como `BranchService._get_company`); mismo orden (`created_at`, `id`) y el mismo
  tope de 20 páginas de 100 (`demasiadas_paginas`).

La membresía `ACTIVE` del `sub` (lo que hoy lee `SQLAlchemyMembershipLookup.active_company_ids`) se resuelve con la
fila de empresa de `v1_operational_access`: la vista elige la membresía `ACTIVE` primero, así que hay alguna activa si
y solo si su causa no es `USER_MEMBERSHIP_INACTIVE`. Todo se aplica en la consulta (FR-037).

Las consultas son síncronas y se ejecutan en un hilo (`run_in_threadpool`). Cualquier error de base →
`DependencyUnavailableError("operational-context")`, el mismo `503` de hoy, con causa `contract:<causa>`; un valor
obligatorio vacío → la misma indisponibilidad que hoy un cuerpo inesperado.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sio_auth import SioPermission
from sio_auth.permissions import has_permission
from sio_auth.tokens import TokenClaims
from sio_contract_read import contract_errors, read
from sio_contract_read.operational_access import OWNER, ROUTE_PERMISSION, read_operational_access
from sqlalchemy import Engine
from starlette.concurrency import run_in_threadpool

from business_reporting_service.application.exceptions import OPERATIONAL_CONTEXT, DependencyUnavailableError
from business_reporting_service.application.ports import BranchInfo, CompanyInfo
from business_reporting_service.infrastructure.operational_context import MAX_PAGES, PAGE_SIZE
from business_reporting_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
_ACCESS = SioPermission(*ROUTE_PERMISSION)
_COMPANIES_READ = SioPermission(OWNER, "companies", "read")
_BRANCHES_READ = SioPermission(OWNER, "branches", "read")
_PLATFORM_ADMINISTER = SioPermission(OWNER, "platform", "administer")
_PLATFORM_LOOKUP = SioPermission(OWNER, "platform", "lookup")
OPERATION = "operational_access"
MAX_BRANCHES = MAX_PAGES * PAGE_SIZE

_MEMBER = (
    "EXISTS (SELECT 1 FROM contract.v1_operational_access a WHERE a.keycloak_user_id = :sub "
    "AND a.company_id = :company_id AND a.branch_id IS NULL "
    "AND a.denial_reason IS DISTINCT FROM 'USER_MEMBERSHIP_INACTIVE')"
)
_COMPANY = "SELECT id, timezone, default_currency FROM contract.v1_companies WHERE id = :company_id"
_BRANCHES = (
    "SELECT id, company_id, code, name, status, effective_timezone FROM contract.v1_branches "
    "WHERE company_id = :company_id AND status = :status"
)
_BRANCHES_ORDER = " ORDER BY created_at, id LIMIT :limit"


def _unavailable(operation: str, cause: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(OPERATIONAL_CONTEXT, operation, f"contract:{cause}")


def _text(operation: str, row: dict, name: str, *, optional: bool = False) -> str | None:
    """Misma regla que `parsing.text_of`: texto obligatorio salvo `optional`; si no, cuerpo inesperado."""
    value = row.get(name)
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise _unavailable(operation, f"cuerpo_inesperado:{name}")
    return value


class ContractOperationalContext:
    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._engine = engine
        self._claims = claims

    def _allows(self, required: SioPermission) -> bool:
        return self._claims is not None and has_permission(self._claims.permissions, required)

    def _rows(self, operation: str, sql: str, params: dict) -> list[dict]:
        with contract_errors(lambda cause: _unavailable(operation, cause), dependency=OPERATIONAL_CONTEXT):
            return read(self._engine, sql, params)

    # ------------------------------------------------------------------ acceso operativo (T031)

    def _read_access(self, company_id: UUID):
        with contract_errors(lambda cause: _unavailable(OPERATION, cause), dependency=OPERATIONAL_CONTEXT):
            return read_operational_access(self._engine, subject=self._claims.subject, company_id=company_id)

    async def has_company_access(self, company_id: UUID) -> bool:
        if not self._allows(_ACCESS):
            logger.info("Operational Context negó el acceso a la empresa estado=%s", 403)
            return False
        access = await run_in_threadpool(self._read_access, company_id)
        return access.allowed and (access.company_id is None or access.company_id == company_id)

    # ------------------------------------------------------------------ empresa y sucursales (T074)

    def _read_company(self, company_id: UUID) -> CompanyInfo | None:
        operation = "company"
        sql, params = _COMPANY, {"company_id": company_id}
        if not (self._allows(_PLATFORM_ADMINISTER) or self._allows(_PLATFORM_LOOKUP)):
            sql, params = f"{sql} AND {_MEMBER}", {**params, "sub": self._claims.subject}
        rows = self._rows(operation, sql, params)
        if not rows:
            return None
        row = rows[0]
        return CompanyInfo(row["id"], _text(operation, row, "timezone", optional=True) or "",
                           _text(operation, row, "default_currency"))

    async def company(self, company_id: UUID) -> CompanyInfo | None:
        if not self._allows(_COMPANIES_READ):
            return None
        return await run_in_threadpool(self._read_company, company_id)

    def _read_branches(self, company_id: UUID, status: str) -> list[BranchInfo]:
        operation = "branches"
        sql, params = _BRANCHES, {"company_id": company_id, "status": status, "limit": MAX_BRANCHES + 1}
        if not self._allows(_PLATFORM_ADMINISTER):
            sql, params = f"{sql} AND {_MEMBER}", {**params, "sub": self._claims.subject}
        rows = self._rows(operation, sql + _BRANCHES_ORDER, params)
        if len(rows) > MAX_BRANCHES:
            raise _unavailable(operation, "demasiadas_paginas")
        return [
            BranchInfo(row["id"], row["company_id"], _text(operation, row, "code"), _text(operation, row, "name"),
                       _text(operation, row, "status"),
                       _text(operation, row, "effective_timezone", optional=True) or "")
            for row in rows
        ]

    async def branches(self, company_id: UUID, *, status: str) -> list[BranchInfo]:
        if not self._allows(_BRANCHES_READ):
            return []
        return await run_in_threadpool(self._read_branches, company_id, status)
