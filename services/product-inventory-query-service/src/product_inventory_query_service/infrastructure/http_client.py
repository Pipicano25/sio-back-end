"""Cliente HTTP asíncrono de las llamadas salientes (Principio XV; FR-022-75, FR-022-76; research R-01).

Aplica en un solo lugar:

- `httpx.AsyncClient` por proveedor (pool de conexiones);
- tiempo de espera = mínimo entre el de la dependencia y lo que queda del presupuesto de la solicitud;
- semáforo de concurrencia de la solicitud;
- propagación de `traceparent` (mismo trace-id, span nuevo);
- un log por llamada con proveedor, operación, estado y duración, **nunca** con tokens, cuerpos ni la URL con
  sus parámetros.

Los errores de red, el tiempo agotado y el presupuesto agotado se traducen a `DependencyUnavailableError`.
`TechnicalCaller` agrega la identidad técnica: un `401` renueva el token una vez y reintenta; un segundo `401`, o
un `403`, es un error de configuración que se registra y responde `503` (FR-022-72).
"""

from __future__ import annotations

import logging
import time
from contextlib import AsyncExitStack
from typing import Any

import httpx

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.ports import TokenProvider
from product_inventory_query_service.application.request_context import current_budget
from product_inventory_query_service.observability import SERVICE_LOGGER, build_traceparent, current_trace_id

logger = logging.getLogger(SERVICE_LOGGER)


class AsyncDependencyClient:
    """Envía solicitudes a un proveedor y registra el resultado."""

    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout_seconds, transport=transport)

    def unavailable(self, operation: str, cause: str) -> DependencyUnavailableError:
        return DependencyUnavailableError(self.provider, operation, cause)

    async def send(
        self,
        operation: str,
        method: str,
        path: str,
        *,
        authorization: str | None,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Envía la solicitud y devuelve la respuesta (cualquier estado HTTP).

        Raises:
            DependencyUnavailableError: tiempo agotado, error de red o presupuesto de la solicitud agotado.
        """
        budget = current_budget()
        timeout = self.timeout_seconds
        if budget is not None:
            remaining = budget.remaining()
            if remaining <= 0:
                logger.warning("Llamada saliente omitida proveedor=%s operacion=%s causa=presupuesto_agotado",
                               self.provider, operation)
                raise self.unavailable(operation, "presupuesto_agotado")
            timeout = min(timeout, remaining)

        headers: dict[str, str] = {}
        if authorization:
            headers["Authorization"] = authorization
        trace_id = current_trace_id()
        if trace_id:
            headers["traceparent"] = build_traceparent(trace_id)

        async with AsyncExitStack() as stack:
            if budget is not None:
                await stack.enter_async_context(budget.semaphore)
            started = time.perf_counter()
            try:
                response = await self._client.request(method, path, headers=headers, json=json, params=params, timeout=timeout)
            except httpx.TimeoutException:
                self._log(operation, "tiempo_agotado", started)
                raise self.unavailable(operation, "tiempo_agotado") from None
            except httpx.HTTPError as exc:
                self._log(operation, f"error_de_red:{type(exc).__name__}", started)
                raise self.unavailable(operation, "error_de_red") from None

        self._log(operation, str(response.status_code), started)
        return response

    def _log(self, operation: str, outcome: str, started: float) -> None:
        logger.info(
            "Llamada saliente proveedor=%s operacion=%s estado=%s duracion_ms=%d",
            self.provider,
            operation,
            outcome,
            int((time.perf_counter() - started) * 1000),
        )

    async def aclose(self) -> None:
        await self._client.aclose()


class TechnicalCaller:
    """Llamadas con la identidad técnica del servicio (D5)."""

    def __init__(self, client: AsyncDependencyClient, tokens: TokenProvider) -> None:
        self.client = client
        self._tokens = tokens

    async def send(self, operation: str, method: str, path: str, *, json: Any = None, params: dict[str, Any] | None = None):
        for attempt in (1, 2):
            token = await self._tokens.token()
            response = await self.client.send(
                operation, method, path, authorization=f"Bearer {token}", json=json, params=params
            )
            if response.status_code == 401 and attempt == 1:
                self._tokens.invalidate()
                continue
            if response.status_code in (401, 403):
                logger.error(
                    "La identidad técnica fue rechazada proveedor=%s operacion=%s estado=%s (revisar el cliente "
                    "y sus permisos en Keycloak)",
                    self.client.provider,
                    operation,
                    response.status_code,
                )
                raise self.client.unavailable(operation, "identidad_tecnica_rechazada")
            return response
        raise self.client.unavailable(operation, "identidad_tecnica_rechazada")  # pragma: no cover

    async def json(self, operation: str, method: str, path: str, **kwargs: Any) -> Any:
        """Envía y exige `200` con JSON; cualquier otro estado o cuerpo es `503`."""
        response = await self.send(operation, method, path, **kwargs)
        if response.status_code != 200:
            raise self.client.unavailable(operation, f"estado={response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise self.client.unavailable(operation, "cuerpo_no_json") from None
