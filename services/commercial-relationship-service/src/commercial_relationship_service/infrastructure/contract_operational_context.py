"""Acceso a la empresa leído de la vista de contrato de Operational Context (spec 025, T028; D27).

Implementa `CompanyAccessDirectory`:

- `check_company_access` lee `contract.v1_operational_access` sin llamar a `GET /operational-access`. Antes exige
  con el token del usuario el permiso de esa ruta (`perm:operational-context:application_users:read`); sin él lanza
  `OperationalAccessDeniedError`, igual que hoy el `403` (FR-037). Las causas se traducen igual que el adaptador
  HTTP.
- `list_member_companies` (resumen de empresas, Historia 4) sigue por HTTP en esta fase.

Cualquier error de base → `DependencyUnavailableError("operational-context")`, el mismo `503` de hoy.
"""

from __future__ import annotations

from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sio_auth.permissions import has_permission
from sio_contract_read import contract_errors
from sio_contract_read.operational_access import ROUTE_PERMISSION, read_operational_access
from sqlalchemy import Engine

from commercial_relationship_service.application.exceptions import OPERATIONAL_CONTEXT, DependencyUnavailableError
from commercial_relationship_service.application.ports import CompanyAccess, MemberCompany
from commercial_relationship_service.infrastructure.http_lookup import logger
from commercial_relationship_service.infrastructure.operational_context_directory import (
    _NOT_MEMBER,
    HTTPCompanyAccessDirectory,
    _forbidden,
)

_REQUIRED = SioPermission(*ROUTE_PERMISSION)
OPERATION = "operational_access"


def _unavailable(cause: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(provider=OPERATIONAL_CONTEXT, cause=f"contract:{cause}", operation=OPERATION)


class ContractCompanyAccessDirectory:
    """`CompanyAccessDirectory` sobre `contract.v1_operational_access` con el `sub` y los permisos del token."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None, http: HTTPCompanyAccessDirectory) -> None:
        self._engine = engine
        self._claims = claims
        self._http = http

    def check_company_access(self, company_id: UUID) -> CompanyAccess:
        if self._claims is None or not has_permission(self._claims.permissions, _REQUIRED):
            raise _forbidden(OPERATION)
        with contract_errors(_unavailable, dependency=OPERATIONAL_CONTEXT):
            access = read_operational_access(self._engine, subject=self._claims.subject, company_id=company_id)
        if access.allowed:
            return CompanyAccess(member_active=True, company_active=True)
        if access.reason in _NOT_MEMBER:
            return CompanyAccess(member_active=False, company_active=None)
        if access.reason == "COMPANY_INACTIVE":
            return CompanyAccess(member_active=True, company_active=False)
        logger.error("Causa inesperada de Operational Context operacion=%s causa=%s", OPERATION, access.reason)
        raise _unavailable(f"causa_inesperada={access.reason}")

    def list_member_companies(self) -> list[MemberCompany]:
        return self._http.list_member_companies()
