"""Acceso operativo leído de ``contract.v1_operational_access`` de Operational Context (spec 025, Historia 3).

Reproduce la vía propia de ``GET /operational-access`` sin ``permission`` (ningún consumidor lo envía):

- sin fila para el ``sub`` y el destino → ``USER_NOT_MEMBER``, con el ``company_id`` pedido (nulo si se pidió una
  sucursal) y sin ``application_user_id``;
- con ``denial_reason`` → esa causa, con la empresa y la membresía de la fila;
- sin causa → permitido.

El permiso de la ruta (``perm:operational-context:application_users:read``) lo comprueba el consumidor con su
token **antes** de llamar, como hace hoy la ruta de Operational Context (FR-037).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Engine

from sio_contract_read.engine import read

OWNER = "operational-context"
ROUTE_PERMISSION = ("operational-context", "application_users", "read")
USER_NOT_MEMBER = "USER_NOT_MEMBER"

_BY_COMPANY = (
    "SELECT company_id, application_user_id, denial_reason FROM contract.v1_operational_access "
    "WHERE keycloak_user_id = :sub AND company_id = :company_id AND branch_id IS NULL"
)
_BY_BRANCH = (
    "SELECT company_id, application_user_id, denial_reason FROM contract.v1_operational_access "
    "WHERE keycloak_user_id = :sub AND branch_id = :branch_id"
)


@dataclass(frozen=True, slots=True)
class OperationalAccess:
    allowed: bool
    reason: str | None
    company_id: UUID | None
    application_user_id: UUID | None


def _uuid(value) -> UUID | None:
    if value is None or isinstance(value, UUID):
        return value
    return UUID(str(value))


def read_operational_access(
    engine: Engine, *, subject: str, company_id: UUID | None = None, branch_id: UUID | None = None
) -> OperationalAccess:
    """Acceso del ``subject`` a una empresa o a una sucursal (exactamente una)."""
    if (company_id is None) == (branch_id is None):
        raise ValueError("Indique exactamente uno de company_id o branch_id.")
    if branch_id is not None:
        rows = read(engine, _BY_BRANCH, {"sub": subject, "branch_id": branch_id})
    else:
        rows = read(engine, _BY_COMPANY, {"sub": subject, "company_id": company_id})
    if not rows:
        return OperationalAccess(False, USER_NOT_MEMBER, company_id, None)
    row = rows[0]
    reason = row["denial_reason"]
    return OperationalAccess(reason is None, reason, _uuid(row["company_id"]), _uuid(row["application_user_id"]))
