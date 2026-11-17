"""Operational Context leído de sus vistas de contrato (spec 025, T028 y T058; D27).

`ContractCompanyAccessDirectory` implementa `CompanyAccessDirectory`:

- `check_company_access` lee `contract.v1_operational_access` sin llamar a `GET /operational-access`. Antes exige
  con el token del usuario el permiso de esa ruta (`perm:operational-context:application_users:read`); sin él lanza
  `OperationalAccessDeniedError`, igual que hoy el `403` (FR-037). Las causas se traducen igual que el adaptador
  HTTP.
- `list_member_companies` (resumen de empresas, Historia 4) lee `contract.v1_user_memberships` en lugar de
  `GET /me/operational-context`, que exige el mismo permiso `application_users:read` (sin él →
  `OperationalAccessDeniedError`, el `403` de hoy). Replica `HTTPCompanyAccessDirectory.list_member_companies`:
  valida que `status` y `company_status` sean `ACTIVE`/`INACTIVE`, toma solo las membresías `ACTIVE`, una por
  empresa, y ordena por `str(company_id)`.

`ContractCompanyDirectory` implementa `CompanyDirectory` sobre `contract.v1_companies` en lugar de
`GET /companies/{id}`, que hoy va con el token del usuario y en Operational Context aplica:

1. el permiso de la ruta `perm:operational-context:companies:read` (`api/companies.py`); sin él, `403`;
2. `CompanyService.get` → empresa inexistente → `404`;
3. `AccessScope.ensure_company_visible(company_id, lookup_read=True)`: visible si el token cubre
   `platform:administer` o `platform:lookup`, o si el `sub` tiene una membresía `ACTIVE` en la empresa
   (`SQLAlchemyMembershipLookup.active_company_ids`, sin mirar el estado de la empresa); si no, el mismo `404`.

La membresía se comprueba en la misma consulta con `contract.v1_user_memberships`. `get_company_organization`
responde `403` → `OperationalAccessDeniedError` y `404` → `NotFoundError`; `find_company_organization` (resumen)
responde `None` en ambos casos, como hoy. `find_company_organizations` es la variante por lote del resumen (T060),
en lotes de 100, con el mismo resultado por empresa.

Sin `TokenClaims` (petición sin token: hoy Operational Context respondería `401`) los métodos nuevos responden la
indisponibilidad del `401` de hoy. Cualquier error de base → `DependencyUnavailableError("operational-context")`, el
mismo `503` de hoy.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sio_auth.permissions import has_permission
from sio_contract_read import chunked, contract_errors
from sio_contract_read.operational_access import ROUTE_PERMISSION, read_operational_access
from sqlalchemy import Engine

from commercial_relationship_service.application.exceptions import (
    OPERATIONAL_CONTEXT,
    DependencyUnavailableError,
    NotFoundError,
)
from commercial_relationship_service.application.ports import CompanyAccess, MemberCompany
from commercial_relationship_service.infrastructure.contract_support import (
    BATCH_LIMIT,
    ContractReader,
    distinct_ids,
    granted,
)
from commercial_relationship_service.infrastructure.http_lookup import logger
from commercial_relationship_service.infrastructure.operational_context_directory import (
    _NOT_MEMBER,
    _STATUSES,
    _forbidden,
)

SERVICE = "operational-context"
_REQUIRED = SioPermission(*ROUTE_PERMISSION)
COMPANIES_READ = SioPermission(SERVICE, "companies", "read")
PLATFORM_ADMINISTER = SioPermission(SERVICE, "platform", "administer")
PLATFORM_LOOKUP = SioPermission(SERVICE, "platform", "lookup")
OPERATION = "operational_access"

_MEMBERSHIPS = (
    "SELECT company_id, status, company_status FROM contract.v1_user_memberships"
    " WHERE keycloak_user_id = :sub ORDER BY created_at, application_user_id"
)
# `:everyone` = el token cubre `platform:administer` o `platform:lookup` (visible sin membresía).
_COMPANIES = (
    "SELECT c.id, c.organization_identity_id FROM contract.v1_companies c"
    " WHERE c.id = ANY(:ids)"
    " AND (CAST(:everyone AS boolean) OR EXISTS ("
    "SELECT 1 FROM contract.v1_user_memberships m"
    " WHERE m.company_id = c.id AND m.keycloak_user_id = :sub AND m.status = 'ACTIVE'))"
)


def _unavailable(cause: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(provider=OPERATIONAL_CONTEXT, cause=f"contract:{cause}", operation=OPERATION)


class ContractCompanyAccessDirectory:
    """`CompanyAccessDirectory` sobre `v1_operational_access` y `v1_user_memberships` con el token del usuario."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._engine = engine
        self._claims = claims
        self._reader = ContractReader(engine, OPERATIONAL_CONTEXT)

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
        operation = "me_operational_context"
        if self._claims is None:
            raise self._reader.unavailable(operation, "estado=401")
        if not granted(self._claims, _REQUIRED):
            raise _forbidden(operation)

        rows = self._reader.rows(operation, _MEMBERSHIPS, {"sub": self._claims.subject})
        companies: dict[UUID, MemberCompany] = {}
        for row in rows:
            if row["status"] not in _STATUSES or row["company_status"] not in _STATUSES:
                raise self._reader.unavailable(operation, "cuerpo_inesperado")
            if row["status"] == "ACTIVE":
                company_id = row["company_id"]
                companies[company_id] = MemberCompany(company_id=company_id, company_status=row["company_status"])

        return sorted(companies.values(), key=lambda company: str(company.company_id))


class ContractCompanyDirectory:
    """`CompanyDirectory` sobre `v1_companies` con el permiso y la visibilidad de `GET /companies/{id}`."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._reader = ContractReader(engine, OPERATIONAL_CONTEXT)
        self._claims = claims

    def get_company_organization(self, company_id: UUID) -> UUID:
        operation = "get_company"
        if self._claims is None:
            raise self._reader.unavailable(operation, "estado=401")
        if not granted(self._claims, COMPANIES_READ):
            raise _forbidden(operation)
        organization_id = self._visible(operation, [company_id]).get(company_id)
        if organization_id is None:
            raise NotFoundError
        return organization_id

    def find_company_organization(self, company_id: UUID) -> UUID | None:
        return self.find_company_organizations([company_id]).get(company_id)

    def find_company_organizations(self, company_ids: Sequence[UUID]) -> dict[UUID, UUID | None]:
        """Variante por lote de `find_company_organization`: `None` donde hoy hay `403` o `404`."""
        operation = "get_company_for_summary"
        if self._claims is None:
            raise self._reader.unavailable(operation, "estado=401")
        if not granted(self._claims, COMPANIES_READ):
            return {company_id: None for company_id in company_ids}
        found = self._visible(operation, distinct_ids(company_ids))
        return {company_id: found.get(company_id) for company_id in company_ids}

    def _visible(self, operation: str, company_ids: list[UUID]) -> dict[UUID, UUID]:
        everyone = granted(self._claims, PLATFORM_ADMINISTER) or granted(self._claims, PLATFORM_LOOKUP)
        found: dict[UUID, UUID] = {}
        for chunk in chunked(company_ids, BATCH_LIMIT):
            rows = self._reader.rows(
                operation, _COMPANIES, {"ids": chunk, "everyone": everyone, "sub": self._claims.subject}
            )
            for row in rows:
                found[row["id"]] = self._reader.required(operation, row, "organization_identity_id")
        return found
