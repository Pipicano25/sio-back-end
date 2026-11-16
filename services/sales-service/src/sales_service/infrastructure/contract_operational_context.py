"""Acceso operativo leído de la vista de contrato de Operational Context (spec 025, T023; D27).

Implementa el mismo puerto que `HTTPAccessDirectory` sin llamar a `GET /operational-access`:

1. exige con el token del usuario el permiso de esa ruta (`perm:operational-context:application_users:read`);
   sin él lanza `OperationalAccessDeniedError`, igual que hoy el `403` del proveedor (FR-037);
2. lee `contract.v1_operational_access` por `sub` y empresa o sucursal (sin fila → `USER_NOT_MEMBER`);
3. cualquier error de base → `DependencyUnavailableError("operational-context")`, el mismo `503` de hoy.
"""

from __future__ import annotations

from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sio_auth.permissions import has_permission
from sio_contract_read import contract_errors
from sio_contract_read.operational_access import ROUTE_PERMISSION, read_operational_access
from sqlalchemy import Engine

from sales_service.application.exceptions import (
    OPERATIONAL_CONTEXT,
    DependencyUnavailableError,
    OperationalAccessDeniedError,
)
from sales_service.application.ports import AccessResult
from sales_service.infrastructure.http_client import logger

_REQUIRED = SioPermission(*ROUTE_PERMISSION)
OPERATION = "operational_access"


def _unavailable(cause: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(OPERATIONAL_CONTEXT, operation=OPERATION, cause=f"contract:{cause}")


class ContractAccessDirectory:
    """`AccessDirectory` sobre `contract.v1_operational_access` con el `sub` y los permisos del token."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._engine = engine
        self._claims = claims

    def _access(self, *, company_id: UUID | None = None, branch_id: UUID | None = None) -> AccessResult:
        if self._claims is None or not has_permission(self._claims.permissions, _REQUIRED):
            logger.warning("Operational Context negó la evaluación de acceso al usuario operacion=%s", OPERATION)
            raise OperationalAccessDeniedError()
        with contract_errors(_unavailable, dependency=OPERATIONAL_CONTEXT):
            access = read_operational_access(
                self._engine, subject=self._claims.subject, company_id=company_id, branch_id=branch_id
            )
        return AccessResult(access.allowed, access.reason, access.company_id, access.application_user_id)

    def check_branch(self, branch_id: UUID) -> AccessResult:
        return self._access(branch_id=branch_id)

    def check_company(self, company_id: UUID) -> AccessResult:
        return self._access(company_id=company_id)
