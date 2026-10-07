"""Acceso de un usuario humano a una sucursal o empresa (R-02, DS-09; `contracts/dependencies.md`).

Traduce `operational-access` (con el token del usuario) a las respuestas de Purchase:

| `operational-access` | Purchase |
| --- | --- |
| `allowed` con `company_id` de la ruta | permitido (`application_user_id` de la membresía) |
| `allowed` con otra empresa | `404` |
| `USER_NOT_MEMBER`, `USER_MEMBERSHIP_INACTIVE` | `404` |
| `BRANCH_NOT_ASSIGNED`, `USER_BRANCH_INACTIVE`, `BRANCH_INACTIVE`, `COMPANY_INACTIVE` | `403 BRANCH_ACCESS_DENIED` (`404` si la sucursal es de otra empresa) |
| `403` del proveedor | `403 OPERATIONAL_ACCESS_DENIED` (lo lanza el puerto) |
| otro | `503 operational-context` |

Las lecturas y las secuencias exigen solo membresía (`company_id`); una empresa inactiva
se puede consultar.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from purchase_service.application.exceptions import (
    OPERATIONAL_CONTEXT,
    BranchAccessDeniedError,
    DependencyUnavailableError,
    NotFoundError,
)
from purchase_service.application.ports import AccessDirectory, AccessResult

NOT_MEMBER = frozenset({"USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE"})
BRANCH_DENIED = frozenset({"BRANCH_NOT_ASSIGNED", "USER_BRANCH_INACTIVE", "BRANCH_INACTIVE", "COMPANY_INACTIVE"})


@dataclass(frozen=True, slots=True)
class OperatorAccess:
    """Usuario humano autorizado y su usuario operativo en la empresa."""

    company_id: UUID
    application_user_id: UUID


def _unexpected(reason: str | None) -> DependencyUnavailableError:
    return DependencyUnavailableError(OPERATIONAL_CONTEXT, operation="operational_access", cause=f"reason={reason}")


def require_branch_access(directory: AccessDirectory, company_id: UUID, branch_id: UUID) -> OperatorAccess:
    """Membresía `ACTIVE` y asignación `ACTIVE` a la sucursal, en la empresa de la ruta (DS-09)."""
    result: AccessResult = directory.check_branch(branch_id)

    if result.allowed:
        if result.company_id != company_id:
            raise NotFoundError()
        if result.application_user_id is None:
            raise _unexpected("sin application_user_id")
        return OperatorAccess(company_id, result.application_user_id)

    if result.reason in NOT_MEMBER:
        raise NotFoundError()

    if result.reason in BRANCH_DENIED:
        if result.company_id is not None and result.company_id != company_id:
            raise NotFoundError()
        raise BranchAccessDeniedError()

    raise _unexpected(result.reason)


def require_membership(directory: AccessDirectory, company_id: UUID) -> AccessResult:
    """Membresía `ACTIVE` en la empresa (lecturas y secuencias); empresa inactiva permitida."""
    result = directory.check_company(company_id)

    if result.reason in NOT_MEMBER:
        raise NotFoundError()

    if result.allowed or result.reason == "COMPANY_INACTIVE":
        return result

    raise _unexpected(result.reason)
