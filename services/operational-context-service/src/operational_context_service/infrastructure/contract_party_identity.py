"""Party Identity leído de sus vistas de contrato (spec 025, T068; D27).

`ContractPartyIdentityPersonDirectory` y `ContractPartyIdentityOrganizationDirectory` implementan `PersonDirectory`
y `OrganizationDirectory` igual que sus adaptadores HTTP, que hoy van con el token del usuario. En Party Identity
cada `GET` por id solo exige el permiso de lectura de su ruta y devuelve la identidad en cualquier estado (sin
reglas de alcance):

| Método | Vista | Reemplaza | Permiso de la ruta |
|---|---|---|---|
| `get_person`, `get_person_profile` | `v1_person_identities` | `GET /person-identities/{id}` | `perm:party-identity:person_identities:read` |
| `get_organization`, `get_organization_profile` | `v1_organization_identities` | `GET /organization-identities/{id}` | `...:organization_identities:read` |

- Sin el permiso o sin token → `DependencyUnavailableError` con la causa de denegación de hoy
  (`PERSON_VALIDATION_DENIED` / `ORGANIZATION_VALIDATION_DENIED`), como el `401`/`403`.
- Sin fila → `None` (el `404`). `status` fuera de `ACTIVE`/`INACTIVE` → la misma indisponibilidad que un cuerpo
  inesperado. Nombres e identificación vacíos → `None`, igual que `_text` del adaptador HTTP.
- Cualquier error de base → `DependencyUnavailableError("party-identity")`, el mismo `503` de hoy.
"""

from __future__ import annotations

from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sqlalchemy import Engine

from operational_context_service.application.exceptions import (
    ORGANIZATION_VALIDATION_DENIED,
    PERSON_VALIDATION_DENIED,
)
from operational_context_service.application.ports import ExternalRef, OrganizationProfile, PersonProfile
from operational_context_service.infrastructure.contract_support import ContractReader, text_or_none

PROVIDER = "party-identity"
SERVICE = "party-identity"
PERSONS_READ = SioPermission(SERVICE, "person_identities", "read")
ORGANIZATIONS_READ = SioPermission(SERVICE, "organization_identities", "read")

_PERSON = (
    "SELECT status, identification_type, identification_number, first_name, middle_name, last_name, second_last_name"
    " FROM contract.v1_person_identities WHERE id = :id"
)
_ORGANIZATION = (
    "SELECT status, legal_name, trade_name, identification_type, identification_number"
    " FROM contract.v1_organization_identities WHERE id = :id"
)


class ContractPartyIdentityPersonDirectory:
    """Personas por UUID desde `v1_person_identities`, con el permiso del usuario."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._reader = ContractReader(engine, provider=PROVIDER, claims=claims, denied_cause=PERSON_VALIDATION_DENIED)

    def get_person(self, person_identity_id: UUID) -> ExternalRef | None:
        operation = "get_person"
        row = self._row(operation, person_identity_id)
        if row is None:
            return None
        return ExternalRef(id=person_identity_id, status=self._reader.status(operation, row))

    def get_person_profile(self, person_identity_id: UUID) -> PersonProfile | None:
        """Nombre e identificación para el listado de empleados por sucursal; no se persisten."""
        operation = "get_person_profile"
        row = self._row(operation, person_identity_id)
        if row is None:
            return None
        return PersonProfile(
            id=person_identity_id,
            status=self._reader.status(operation, row),
            identification_type=text_or_none(row.get("identification_type")),
            identification_number=text_or_none(row.get("identification_number")),
            first_name=text_or_none(row.get("first_name")),
            middle_name=text_or_none(row.get("middle_name")),
            last_name=text_or_none(row.get("last_name")),
            second_last_name=text_or_none(row.get("second_last_name")),
        )

    def _row(self, operation: str, person_identity_id: UUID) -> dict | None:
        self._reader.require(operation, PERSONS_READ)
        return self._reader.one(operation, _PERSON, {"id": person_identity_id})


class ContractPartyIdentityOrganizationDirectory:
    """Organizaciones por UUID desde `v1_organization_identities`, con el permiso del usuario."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._reader = ContractReader(
            engine, provider=PROVIDER, claims=claims, denied_cause=ORGANIZATION_VALIDATION_DENIED
        )

    def get_organization(self, organization_identity_id: UUID) -> ExternalRef | None:
        operation = "get_organization"
        row = self._row(operation, organization_identity_id)
        if row is None:
            return None
        return ExternalRef(id=organization_identity_id, status=self._reader.status(operation, row))

    def get_organization_profile(self, organization_identity_id: UUID) -> OrganizationProfile | None:
        """Nombre e identificación para mostrarlos en `/me/operational-context`; no se persisten."""
        operation = "get_organization_profile"
        row = self._row(operation, organization_identity_id)
        if row is None:
            return None
        return OrganizationProfile(
            id=organization_identity_id,
            status=self._reader.status(operation, row),
            legal_name=text_or_none(row.get("legal_name")),
            trade_name=text_or_none(row.get("trade_name")),
            identification_type=text_or_none(row.get("identification_type")),
            identification_number=text_or_none(row.get("identification_number")),
        )

    def _row(self, operation: str, organization_identity_id: UUID) -> dict | None:
        self._reader.require(operation, ORGANIZATIONS_READ)
        return self._reader.one(operation, _ORGANIZATION, {"id": organization_identity_id})
