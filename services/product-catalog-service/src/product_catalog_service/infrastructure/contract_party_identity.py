"""Fabricante leído de la vista de contrato de Party Identity (spec 025, T071; D27).

`ContractPartyIdentityManufacturerDirectory` implementa `ManufacturerDirectory` igual que
`HTTPPartyIdentityManufacturerDirectory`, que hoy consulta `GET /organization-identities/{id}` con el **token del
usuario**. Esa ruta de Party Identity solo exige `perm:party-identity:organization_identities:read` y devuelve la
organización en cualquier estado (sin reglas de alcance), así que:

- sin `TokenClaims` (hoy Party Identity respondería `401`) o sin ese permiso en el token (hoy `403`) →
  `ManufacturerDirectoryAccessDeniedError`, como hoy (FR-037);
- fila en `contract.v1_organization_identities` → `True` (el `200` de hoy); sin fila → `False` (el `404`);
- cualquier error de base (conexión, `statement_timeout`, pool agotado, permiso) →
  `ManufacturerDirectoryUnavailableError`, el mismo `503` de hoy, con causa `contract:<causa>`.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import Request
from sio_auth import SioPermission, TokenClaims
from sio_auth.permissions import has_permission
from sio_contract_read import contract_errors, read_one
from sqlalchemy import Engine

from product_catalog_service.application.exceptions import (
    ManufacturerDirectoryAccessDeniedError,
    ManufacturerDirectoryUnavailableError,
)

logger = logging.getLogger(__name__)

PARTY_IDENTITY = "party-identity"
ORGANIZATIONS_READ = SioPermission(PARTY_IDENTITY, "organization_identities", "read")
_ORGANIZATION = "SELECT 1 AS found FROM contract.v1_organization_identities WHERE id = :id"


def _unavailable(cause: str) -> ManufacturerDirectoryUnavailableError:
    logger.error("Dependencia no disponible causa=contract:%s proveedor=%s", cause, PARTY_IDENTITY)
    return ManufacturerDirectoryUnavailableError(f"No fue posible consultar Party Identity Service (contract:{cause}).")


class ContractPartyIdentityManufacturerDirectory:
    """Existencia de la organización fabricante desde `v1_organization_identities`, con el permiso del token."""

    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._engine = engine
        self._claims = claims

    def exists(self, organization_id: UUID) -> bool:
        if self._claims is None or not has_permission(self._claims.permissions, ORGANIZATIONS_READ):
            raise ManufacturerDirectoryAccessDeniedError(
                "Party Identity Service rechazó la consulta de la organización."
            )
        with contract_errors(_unavailable, dependency=PARTY_IDENTITY):
            row = read_one(self._engine, _ORGANIZATION, {"id": organization_id})
        return row is not None


def build_contract_manufacturer_directory(
    request: Request, engine: Engine
) -> ContractPartyIdentityManufacturerDirectory:
    """Adaptador de la solicitud actual con los `TokenClaims` que `sio-auth` dejó en ella."""
    return ContractPartyIdentityManufacturerDirectory(
        engine=engine, claims=getattr(request.state, "sio_claims", None)
    )
