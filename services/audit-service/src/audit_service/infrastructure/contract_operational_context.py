"""Acceso a la empresa leído de la vista de contrato de Operational Context (spec 025, T029; D27).

Implementa `check_company_access` igual que `HTTPCompanyAccessDirectory`, sin llamar a `GET /operational-access`:

1. exige con el token del usuario el permiso de esa ruta (`perm:operational-context:application_users:read`);
   sin él lanza `OperationalAccessDeniedError` con el mismo mensaje que el `403` de hoy (FR-037);
2. lee `contract.v1_operational_access` por `sub` y empresa: miembro activo o empresa inactiva → miembro;
   sin fila o membresía inactiva → no miembro;
3. cualquier error de base → `DependencyUnavailableError("operational-context")`, el mismo `503` de hoy.
"""

from __future__ import annotations

from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sio_auth.permissions import has_permission
from sio_contract_read import contract_errors
from sio_contract_read.operational_access import ROUTE_PERMISSION, read_operational_access
from sqlalchemy import Engine

from audit_service.application.exceptions import DependencyUnavailableError, OperationalAccessDeniedError
from audit_service.application.ports import CompanyAccess
from audit_service.infrastructure.http_lookup import logger
from audit_service.infrastructure.operational_context_directory import _NOT_MEMBER, OPERATIONAL_CONTEXT

_REQUIRED = SioPermission(*ROUTE_PERMISSION)
OPERATION = "operational_access"
_DENIED = (
    "No tiene permiso para consultar el acceso operativo requerido. Solicite acceso "
    "al administrador del sistema indicando el trace_id."
)


def _unavailable(cause: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(OPERATIONAL_CONTEXT, operation=OPERATION, cause=f"contract:{cause}")


class ContractCompanyAccessDirectory:
    """Membresía del usuario en una empresa sobre `contract.v1_operational_access`."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._engine = engine
        self._claims = claims

    def check_company_access(self, company_id: UUID) -> CompanyAccess:
        if self._claims is None or not has_permission(self._claims.permissions, _REQUIRED):
            logger.warning("Operational Context negó la evaluación de acceso al usuario operacion=%s", OPERATION)
            raise OperationalAccessDeniedError(_DENIED)
        with contract_errors(_unavailable, dependency=OPERATIONAL_CONTEXT):
            access = read_operational_access(self._engine, subject=self._claims.subject, company_id=company_id)
        if access.allowed:
            return CompanyAccess(member_active=True)
        if access.reason in _NOT_MEMBER:
            return CompanyAccess(member_active=False)
        if access.reason == "COMPANY_INACTIVE":
            return CompanyAccess(member_active=True)
        logger.error("Causa inesperada de Operational Context operacion=%s causa=%s", OPERATION, access.reason)
        raise _unavailable(f"causa_inesperada={access.reason}")
