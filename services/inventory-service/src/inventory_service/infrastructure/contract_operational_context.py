"""Acceso operativo leído de la vista de contrato de Operational Context (spec 025, T027; D27).

Implementa el mismo puerto que `HTTPCompanyAccessDirectory` (`is_member`, `check_branch`, `check_company`) sin
llamar a `GET /operational-access`:

1. exige con el token del usuario el permiso de esa ruta (`perm:operational-context:application_users:read`);
   sin él lanza `OperationalAccessDeniedError`, igual que hoy el `403` del proveedor (FR-037);
2. lee `contract.v1_operational_access` por `sub` y empresa o sucursal (sin fila → `USER_NOT_MEMBER`);
3. `is_member` aplica las mismas reglas que hoy: `COMPANY_INACTIVE` cuenta como miembro en lecturas (R-08);
4. cualquier error de base → `DependencyUnavailableError("operational-context")`, el mismo `503` de hoy.
"""

from __future__ import annotations

from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sio_auth.permissions import has_permission
from sio_contract_read import contract_errors
from sio_contract_read.operational_access import ROUTE_PERMISSION, read_operational_access
from sqlalchemy import Engine

from inventory_service.application.exceptions import (
    OPERATIONAL_CONTEXT,
    DependencyUnavailableError,
    OperationalAccessDeniedError,
)
from inventory_service.application.ports import BranchAccessResult
from inventory_service.infrastructure.http_lookup import logger
from inventory_service.infrastructure.operational_context_directory import _ALLOWED_REASONS_FOR_READS, _NOT_MEMBER

_REQUIRED = SioPermission(*ROUTE_PERMISSION)
OPERATION = "operational_access"


def _unavailable(cause: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(OPERATIONAL_CONTEXT, operation=OPERATION, cause=f"contract:{cause}")


class ContractCompanyAccessDirectory:
    """Acceso del usuario sobre `contract.v1_operational_access` con el `sub` y los permisos del token."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._engine = engine
        self._claims = claims

    def _access(self, *, company_id: UUID | None = None, branch_id: UUID | None = None) -> BranchAccessResult:
        if self._claims is None or not has_permission(self._claims.permissions, _REQUIRED):
            logger.warning("Operational Context negó la evaluación de acceso al usuario operacion=%s", OPERATION)
            raise OperationalAccessDeniedError()
        with contract_errors(_unavailable, dependency=OPERATIONAL_CONTEXT):
            access = read_operational_access(
                self._engine, subject=self._claims.subject, company_id=company_id, branch_id=branch_id
            )
        return BranchAccessResult(access.allowed, access.reason, access.company_id, access.application_user_id)

    def is_member(self, company_id: UUID) -> bool:
        result = self._access(company_id=company_id)
        if result.allowed:
            return True
        if result.reason in _NOT_MEMBER:
            return False
        if result.reason in _ALLOWED_REASONS_FOR_READS:
            return True
        logger.error("Causa inesperada de Operational Context operacion=%s causa=%s", OPERATION, result.reason)
        raise _unavailable(f"causa_inesperada={result.reason}")

    def check_branch(self, branch_id: UUID) -> BranchAccessResult:
        return self._access(branch_id=branch_id)

    def check_company(self, company_id: UUID) -> BranchAccessResult:
        return self._access(company_id=company_id)
