"""Party Identity leído de sus vistas de contrato (spec 025, T059; D27).

`ContractPartyDirectory` implementa `PartyDirectory` igual que `HTTPPartyDirectory`, que hoy va con el token del
usuario. En Party Identity cada `GET` por id solo exige el permiso de lectura de su ruta y devuelve el registro en
cualquier estado (`get_by_id` de cada servicio, sin reglas de alcance):

| Método | Vista | Reemplaza | Permiso de la ruta |
|---|---|---|---|
| `get_person` | `v1_person_identities` | `GET /person-identities/{id}` | `perm:party-identity:person_identities:read` |
| `get_organization` | `v1_organization_identities` | `GET /organization-identities/{id}` | `...:organization_identities:read` |
| `get_contact_person` | `v1_organization_contact_persons` | `GET /organization-contact-persons/{id}` | `...:organization_contact_persons:read` |
| `find_organization_name` | `v1_organization_identities` (`legal_name`) | `GET /organization-identities/{id}` | `...:organization_identities:read` |

- Sin el permiso: `get_*` lanzan `PartyIdentityAccessDeniedError` (el `403` de hoy) y `find_organization_name`
  devuelve `None`, como hoy. Sin fila (`404`) → `None`.
- `status` fuera de `ACTIVE`/`INACTIVE`, `is_active` no booleano o `legal_name` no textual → la misma
  indisponibilidad que hoy produce un cuerpo inesperado.
- Sin `TokenClaims` (hoy Party Identity respondería `401`) → indisponibilidad. Cualquier error de base →
  `DependencyUnavailableError("party-identity")`, el mismo `503` de hoy.

`find_organization_names` es la variante por lote del resumen de empresas (T060), en lotes de 100.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sio_contract_read import chunked
from sqlalchemy import Engine

from commercial_relationship_service.application.exceptions import (
    PARTY_IDENTITY,
    PARTY_IDENTITY_FORBIDDEN,
    PartyIdentityAccessDeniedError,
)
from commercial_relationship_service.application.ports import ContactPersonRef, IdentityRef
from commercial_relationship_service.infrastructure.contract_support import (
    BATCH_LIMIT,
    ContractReader,
    distinct_ids,
    granted,
)
from commercial_relationship_service.infrastructure.http_lookup import logger

SERVICE = "party-identity"
PERSONS_READ = SioPermission(SERVICE, "person_identities", "read")
ORGANIZATIONS_READ = SioPermission(SERVICE, "organization_identities", "read")
CONTACTS_READ = SioPermission(SERVICE, "organization_contact_persons", "read")

_PERSON = "SELECT status FROM contract.v1_person_identities WHERE id = :id"
_ORGANIZATION = "SELECT status FROM contract.v1_organization_identities WHERE id = :id"
_CONTACT = "SELECT organization_identity_id, is_active FROM contract.v1_organization_contact_persons WHERE id = :id"
_NAMES = "SELECT id, legal_name FROM contract.v1_organization_identities WHERE id = ANY(:ids)"


class ContractPartyDirectory:
    """Personas, organizaciones y personas de contacto por UUID desde las vistas de Party Identity."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._reader = ContractReader(engine, PARTY_IDENTITY)
        self._claims = claims

    def get_person(self, person_identity_id: UUID) -> IdentityRef | None:
        return self._identity("get_person", PERSONS_READ, _PERSON, person_identity_id)

    def get_organization(self, organization_identity_id: UUID) -> IdentityRef | None:
        return self._identity("get_organization", ORGANIZATIONS_READ, _ORGANIZATION, organization_identity_id)

    def get_contact_person(self, contact_person_id: UUID) -> ContactPersonRef | None:
        operation = "get_contact_person"
        self._require(operation, CONTACTS_READ)
        row = self._reader.one(operation, _CONTACT, {"id": contact_person_id})
        if row is None:
            return None
        is_active = row.get("is_active")
        if not isinstance(is_active, bool):
            raise self._reader.unavailable(operation, "cuerpo_inesperado")
        return ContactPersonRef(
            id=contact_person_id,
            organization_identity_id=self._reader.required(operation, row, "organization_identity_id"),
            is_active=is_active,
        )

    def find_organization_name(self, organization_identity_id: UUID) -> str | None:
        return self.find_organization_names([organization_identity_id]).get(organization_identity_id)

    def find_organization_names(self, organization_identity_ids: Sequence[UUID]) -> dict[UUID, str | None]:
        """Variante por lote de `find_organization_name`: `None` donde hoy hay `403` o `404`."""
        operation = "get_organization_name"
        if self._claims is None:
            raise self._reader.unavailable(operation, "estado=401")
        if not granted(self._claims, ORGANIZATIONS_READ):
            return {identity_id: None for identity_id in organization_identity_ids}
        names: dict[UUID, str] = {}
        for chunk in chunked(distinct_ids(organization_identity_ids), BATCH_LIMIT):
            for row in self._reader.rows(operation, _NAMES, {"ids": chunk}):
                name = row.get("legal_name")
                if not isinstance(name, str):
                    raise self._reader.unavailable(operation, "cuerpo_inesperado")
                names[row["id"]] = name
        return {identity_id: names.get(identity_id) for identity_id in organization_identity_ids}

    def _identity(self, operation: str, required: SioPermission, sql: str, identity_id: UUID) -> IdentityRef | None:
        self._require(operation, required)
        row = self._reader.one(operation, sql, {"id": identity_id})
        if row is None:
            return None
        status = row.get("status")
        if status not in {"ACTIVE", "INACTIVE"}:
            raise self._reader.unavailable(operation, "cuerpo_inesperado")
        return IdentityRef(id=identity_id, status=status)

    def _require(self, operation: str, required: SioPermission) -> None:
        if self._claims is None:
            raise self._reader.unavailable(operation, "estado=401")
        if not granted(self._claims, required):
            logger.log(
                logging.WARNING,
                "Party Identity negó la consulta al usuario causa=%s operacion=%s",
                PARTY_IDENTITY_FORBIDDEN,
                operation,
            )
            raise PartyIdentityAccessDeniedError()
