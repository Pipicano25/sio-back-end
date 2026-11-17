"""Apoyo común de las lecturas por vistas de contrato de Operational Context (spec 025, T068; D27).

Cada adaptador de contrato implementa el mismo puerto que su adaptador HTTP y responde igual:

- fila encontrada → el mismo objeto que construye hoy el adaptador HTTP;
- sin fila → `None`, como el `404` de hoy;
- hoy la llamada va con el token del usuario y el propietario exige `perm:<propietario>:<recurso>:read`: sin
  `TokenClaims` (el `401` de hoy) o sin ese permiso (el `403`) → la misma `DependencyUnavailableError` con la causa
  de denegación de hoy (FR-037);
- cualquier error de base (conexión, `statement_timeout`, pool agotado, permiso) o una columna obligatoria vacía o
  fuera de contrato → la misma `DependencyUnavailableError` de hoy (`503 DEPENDENCY_UNAVAILABLE`), con causa
  `contract:<causa>`.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sio_auth import SioPermission, TokenClaims
from sio_auth.permissions import has_permission
from sio_contract_read import contract_errors
from sio_contract_read.engine import read
from sqlalchemy import Engine

from operational_context_service.application.exceptions import DependencyUnavailableError
from operational_context_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

VALID_STATUSES = {"ACTIVE", "INACTIVE"}


class ContractReader:
    """Consultas de solo lectura contra las vistas `contract.v1_*` de un propietario, con el permiso del usuario."""

    def __init__(self, engine: Engine, *, provider: str, claims: TokenClaims | None, denied_cause: str) -> None:
        self._engine = engine
        self._claims = claims
        self.provider = provider
        self.denied_cause = denied_cause

    def require(self, operation: str, required: SioPermission) -> None:
        """El mismo permiso que exige hoy la ruta del propietario; si falta, la misma denegación que el `401`/`403`."""
        if self._claims is None:
            raise self._denied(operation, "estado=401")
        if not has_permission(self._claims.permissions, required):
            raise self._denied(operation, "estado=403")

    def one(self, operation: str, sql: str, params: Mapping[str, Any]) -> dict[str, Any] | None:
        with contract_errors(lambda cause: self.unavailable(operation, cause), dependency=self.provider):
            found = read(self._engine, sql, params)
        return found[0] if found else None

    def status(self, operation: str, row: Mapping[str, Any]) -> str:
        value = row.get("status")
        if value not in VALID_STATUSES:
            raise self.unavailable(operation, "cuerpo_inesperado:status")
        return value

    def uuid(self, operation: str, row: Mapping[str, Any], name: str) -> UUID:
        value = row.get(name)
        if not isinstance(value, UUID):
            raise self.unavailable(operation, f"cuerpo_inesperado:{name}")
        return value

    def unavailable(self, operation: str, cause: str) -> DependencyUnavailableError:
        logger.error(
            "Dependencia no disponible causa=contract:%s proveedor=%s operacion=%s", cause, self.provider, operation
        )
        return DependencyUnavailableError(provider=self.provider, cause=f"contract:{cause}", operation=operation)

    def _denied(self, operation: str, outcome: str) -> DependencyUnavailableError:
        logger.warning(
            "No fue posible validar contra la dependencia causa=%s proveedor=%s operacion=%s resultado=%s",
            self.denied_cause,
            self.provider,
            operation,
            outcome,
        )
        return DependencyUnavailableError(provider=self.provider, cause=self.denied_cause, operation=operation)


def text_or_none(value: object) -> str | None:
    """La misma normalización `_text` de los adaptadores HTTP: texto vacío o no textual → `None`."""
    return value if isinstance(value, str) and value.strip() else None
