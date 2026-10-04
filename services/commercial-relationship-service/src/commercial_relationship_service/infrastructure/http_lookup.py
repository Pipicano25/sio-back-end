"""Cliente HTTP común de las llamadas salientes (Principio XV, R-15).

Aplica en un solo lugar: tiempo de espera por llamada, propagación del
`Authorization` recibido y del `traceparent` (mismo trace-id W3C, `span-id`
nuevo) y un log por llamada con proveedor, operación, estado y duración que
nunca incluye tokens ni cuerpos. Los errores de red y tiempo agotado se
traducen a `DependencyUnavailableError`; cada adaptador interpreta los estados
HTTP según su contrato.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from commercial_relationship_service.application.exceptions import DependencyUnavailableError
from commercial_relationship_service.observability import (
    SERVICE_LOGGER,
    build_traceparent,
    current_trace_id,
)

logger = logging.getLogger(SERVICE_LOGGER)


class HTTPDependencyClient:
    """Envía solicitudes a un proveedor y registra el resultado."""

    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        timeout_seconds: float,
        unavailable_cause: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.unavailable_cause = unavailable_cause
        self.transport = transport

    def send(
        self,
        operation: str,
        method: str,
        path: str,
        *,
        authorization: str | None,
        json: Any = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Envía la solicitud y devuelve la respuesta (cualquier estado HTTP).

        Raises:
            DependencyUnavailableError: Ante tiempo agotado o error de red.
        """
        headers: dict[str, str] = {}

        if authorization:
            headers["Authorization"] = authorization

        trace_id = current_trace_id()

        if trace_id:
            headers["traceparent"] = build_traceparent(trace_id)

        started = time.perf_counter()

        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=headers,
                    json=json,
                    params=params,
                )
        except httpx.HTTPError as exc:
            raise self.unavailable(
                operation, started, cause=self.unavailable_cause, outcome=type(exc).__name__
            ) from None

        logger.info(
            "Llamada saliente proveedor=%s operacion=%s estado=%s duracion_ms=%s",
            self.provider,
            operation,
            response.status_code,
            round((time.perf_counter() - started) * 1000),
        )
        return response

    def unavailable(
        self,
        operation: str,
        started: float | None = None,
        *,
        cause: str | None = None,
        outcome: str,
    ) -> DependencyUnavailableError:
        """Registra y construye el error de indisponibilidad (causa solo en el log)."""
        duration_ms = round((time.perf_counter() - started) * 1000) if started else None
        real_cause = cause or self.unavailable_cause
        logger.error(
            "Dependencia no disponible causa=%s proveedor=%s operacion=%s resultado=%s "
            "duracion_ms=%s",
            real_cause,
            self.provider,
            operation,
            outcome,
            duration_ms,
        )
        return DependencyUnavailableError(
            provider=self.provider, cause=real_cause, operation=operation
        )


def json_object(response: httpx.Response) -> dict[str, Any] | None:
    """Cuerpo JSON de la respuesta si es un objeto; `None` si no lo es."""
    try:
        body = response.json()
    except ValueError:
        return None

    return body if isinstance(body, dict) else None
