"""Apoyo común de los adaptadores de lectura por vistas de contrato de Commercial Relationship (spec 025, D27).

Cada adaptador de contrato implementa el mismo puerto que su adaptador HTTP y responde igual:

- fila encontrada → el mismo objeto que construye hoy el adaptador HTTP;
- sin fila → `None` o `NotFoundError`, como el `404` de hoy;
- cualquier error de base (conexión, `statement_timeout`, pool agotado, permiso) o una columna obligatoria vacía o
  fuera de contrato → `DependencyUnavailableError(<proveedor>)`, el mismo `503` de hoy, con causa `contract:<causa>`.

Las lecturas que hoy van con el token del usuario comprueban antes, con los `TokenClaims` de la solicitud, el mismo
permiso que exige la ruta del propietario (FR-037).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sio_auth.permissions import has_permission
from sio_contract_read import contract_errors
from sio_contract_read.engine import read
from sqlalchemy import Engine

from commercial_relationship_service.application.exceptions import DependencyUnavailableError
from commercial_relationship_service.infrastructure.http_lookup import logger

BATCH_LIMIT = 100


class ContractReader:
    """Consultas de solo lectura contra las vistas `contract.v1_*` de un propietario."""

    def __init__(self, engine: Engine, provider: str) -> None:
        self._engine = engine
        self.provider = provider

    def unavailable(self, operation: str, cause: str) -> DependencyUnavailableError:
        logger.error(
            "Dependencia no disponible causa=contract:%s proveedor=%s operacion=%s", cause, self.provider, operation
        )
        return DependencyUnavailableError(provider=self.provider, cause=f"contract:{cause}", operation=operation)

    def rows(self, operation: str, sql: str, params: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        with contract_errors(lambda cause: self.unavailable(operation, cause), dependency=self.provider):
            return read(self._engine, sql, params)

    def one(self, operation: str, sql: str, params: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
        found = self.rows(operation, sql, params)
        return found[0] if found else None

    def required(self, operation: str, row: Mapping[str, Any], name: str) -> Any:
        """Valor obligatorio de la fila; vacío → la misma indisponibilidad que un cuerpo inesperado."""
        value = row.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise self.unavailable(operation, f"cuerpo_inesperado:{name}")
        return value


def granted(claims: TokenClaims | None, required: SioPermission) -> bool:
    """El token cubre el permiso (misma regla `grant.allows` que aplica `sio-auth` en la ruta del propietario)."""
    return claims is not None and has_permission(claims.permissions, required)


def distinct_ids(ids: Sequence[UUID]) -> list[UUID]:
    return list(dict.fromkeys(ids))
