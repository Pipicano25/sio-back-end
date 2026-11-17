"""Acceso operativo leído de la vista de contrato de Operational Context (spec 025, T027; D27).

Implementa el mismo puerto que `HTTPCompanyAccessDirectory` (`is_member`, `check_branch`, `check_company`) sin
llamar a `GET /operational-access`:

1. exige con el token del usuario el permiso de esa ruta (`perm:operational-context:application_users:read`);
   sin él lanza `OperationalAccessDeniedError`, igual que hoy el `403` del proveedor (FR-037);
2. lee `contract.v1_operational_access` por `sub` y empresa o sucursal (sin fila → `USER_NOT_MEMBER`);
3. `is_member` aplica las mismas reglas que hoy: `COMPANY_INACTIVE` cuenta como miembro en lecturas (R-08);
4. cualquier error de base → `DependencyUnavailableError("operational-context")`, el mismo `503` de hoy.

`ContractOperationalContextDirectory` (T063) implementa el puerto de `HTTPOperationalContextDirectory` sobre
`v1_branches`, `v1_application_users` y `v1_companies` (hoy con la identidad técnica de Inventory). Sin fila → `None`
(el `404` de hoy). Conserva las validaciones de forma: `default_currency` cumple `^[A-Z]{3}$` y `keycloak_user_id`
que no sea un UUID queda en `None`, igual que hoy.
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
from inventory_service.application.ports import ApplicationUserInfo, BranchAccessResult, BranchInfo
from inventory_service.infrastructure.contract_support import ContractReader
from inventory_service.infrastructure.http_lookup import logger
from inventory_service.infrastructure.operational_context_directory import (
    _ALLOWED_REASONS_FOR_READS,
    _CURRENCY,
    _NOT_MEMBER,
    _uuid,
)

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


_BRANCH = "SELECT company_id, status, company_status FROM contract.v1_branches WHERE id = :id"
_USER = "SELECT company_id, status, keycloak_user_id FROM contract.v1_application_users WHERE id = :id"
_COMPANY = "SELECT default_currency FROM contract.v1_companies WHERE id = :id"


class ContractOperationalContextDirectory:
    """Sucursal, usuario operativo y moneda de la empresa leídos de las vistas (reemplaza la identidad técnica)."""

    def __init__(self, *, engine: Engine) -> None:
        self._reader = ContractReader(engine, OPERATIONAL_CONTEXT)

    def get_branch(self, branch_id: UUID) -> BranchInfo | None:
        operation = "branch"
        row = self._reader.one(operation, _BRANCH, {"id": branch_id})
        if row is None:
            return None
        required = self._reader.required
        return BranchInfo(
            id=branch_id,
            company_id=required(operation, row, "company_id"),
            status=required(operation, row, "status"),
            company_status=required(operation, row, "company_status"),
        )

    def get_application_user(self, application_user_id: UUID) -> ApplicationUserInfo | None:
        operation = "application_user"
        row = self._reader.one(operation, _USER, {"id": application_user_id})
        if row is None:
            return None
        required = self._reader.required
        return ApplicationUserInfo(
            id=application_user_id,
            company_id=required(operation, row, "company_id"),
            status=required(operation, row, "status"),
            keycloak_user_id=_uuid(row.get("keycloak_user_id")),
        )

    def get_company_currency(self, company_id: UUID) -> str | None:
        operation = "company"
        row = self._reader.one(operation, _COMPANY, {"id": company_id})
        if row is None:
            return None
        currency = row.get("default_currency")
        if not isinstance(currency, str) or not _CURRENCY.match(currency):
            raise self._reader.unavailable(operation, "cuerpo_inesperado:default_currency")
        return currency
