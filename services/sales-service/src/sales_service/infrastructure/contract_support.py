"""Apoyo común de los adaptadores de lectura por vistas de contrato de Sales (spec 025, D27).

Cada adaptador de contrato implementa el mismo puerto que su adaptador HTTP y responde igual:

- fila encontrada → el mismo objeto que construye hoy el adaptador HTTP;
- sin fila → `None` o ausencia, como el `404` / `found=false` de hoy;
- cualquier error de base (conexión, `statement_timeout`, pool agotado, permiso) o una columna obligatoria vacía →
  `DependencyUnavailableError(<proveedor>)`, el mismo `503` de hoy, con causa `contract:<causa>`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sio_contract_read import contract_errors
from sio_contract_read.engine import read
from sqlalchemy import Engine

from sales_service.application.exceptions import DependencyUnavailableError

BATCH_LIMIT = 100


class ContractReader:
    """Consultas de solo lectura contra las vistas `contract.v1_*` de un propietario."""

    def __init__(self, engine: Engine, provider: str) -> None:
        self._engine = engine
        self.provider = provider

    def unavailable(self, operation: str, cause: str) -> DependencyUnavailableError:
        return DependencyUnavailableError(self.provider, operation=operation, cause=f"contract:{cause}")

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


def distinct_ids(ids: Sequence[UUID]) -> list[UUID]:
    return list(dict.fromkeys(ids))
