"""Apoyo común de los adaptadores de lectura por vistas de contrato de PIQ (spec 025, T073; D27).

Cada adaptador de contrato implementa el mismo puerto asíncrono que su adaptador HTTP y responde igual:

- filas encontradas → los mismos objetos que construye hoy el adaptador HTTP;
- sin fila → ausencia en el resultado, como el `found=false` (o el elemento vacío) de hoy;
- cualquier error de base (conexión, `statement_timeout`, pool agotado, permiso) o una columna obligatoria vacía →
  `DependencyUnavailableError(<proveedor>, <operación>, "contract:<causa>")`, el mismo `503` de hoy.

Las consultas son síncronas (SQLAlchemy) y se ejecutan en un hilo con `run_in_threadpool` para no bloquear el bucle.
Igual que `AsyncDependencyClient.send`, no se consulta si el presupuesto de la solicitud ya se agotó.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from sio_contract_read import contract_errors
from sio_contract_read.engine import read
from sqlalchemy import Engine
from starlette.concurrency import run_in_threadpool

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.request_context import current_budget
from product_inventory_query_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
BATCH_LIMIT = 100
T = TypeVar("T")


class ContractReader:
    """Consultas de solo lectura contra las vistas `contract.v1_*` de un propietario."""

    def __init__(self, engine: Engine, provider: str) -> None:
        self._engine = engine
        self.provider = provider

    def unavailable(self, operation: str, cause: str) -> DependencyUnavailableError:
        logger.error(
            "Dependencia no disponible causa=contract:%s proveedor=%s operacion=%s", cause, self.provider, operation
        )
        return DependencyUnavailableError(self.provider, operation, f"contract:{cause}")

    def rows(self, operation: str, sql: str, params: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
        with contract_errors(lambda cause: self.unavailable(operation, cause), dependency=self.provider):
            return read(self._engine, sql, params)

    def required(self, operation: str, row: Mapping[str, Any], name: str) -> Any:
        """Valor obligatorio de la fila; vacío → la misma indisponibilidad que un cuerpo inesperado."""
        value = row.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise self.unavailable(operation, f"cuerpo_inesperado:{name}")
        return value

    async def run(self, operation: str, function: Callable[..., T], *args: Any) -> T:
        """Ejecuta la lectura síncrona en un hilo, salvo que el presupuesto de la solicitud ya se haya agotado."""
        budget = current_budget()
        if budget is not None and budget.remaining() <= 0:
            logger.warning("Lectura de contrato omitida proveedor=%s operacion=%s causa=presupuesto_agotado",
                           self.provider, operation)
            raise DependencyUnavailableError(self.provider, operation, "presupuesto_agotado")
        return await run_in_threadpool(function, *args)


def distinct(values: list) -> list:
    return list(dict.fromkeys(values))
