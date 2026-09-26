"""Cliente HTTP común de consultas por UUID a otros microservicios (R-03, R-06).

Aplica en un solo lugar lo que exigen FR-042 y FR-043: tiempo de espera por
llamada, propagación del `Authorization` del usuario y del `traceparent` (mismo
W3C trace-id, `span-id` nuevo), interpretación de `401`/`403` y fallos como
indisponibilidad, y un log con causa, proveedor, operación, estado y duración
que nunca incluye el token ni el cuerpo.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from operational_context_service.application.exceptions import DependencyUnavailableError
from operational_context_service.observability import (
    SERVICE_LOGGER,
    build_traceparent,
    current_trace_id,
)

logger = logging.getLogger(SERVICE_LOGGER)


class HTTPLookupClient:
    """Consulta un recurso por UUID y clasifica la respuesta."""

    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float,
        denied_cause: str,
        unavailable_cause: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.authorization = authorization
        self.timeout_seconds = timeout_seconds
        self.denied_cause = denied_cause
        self.unavailable_cause = unavailable_cause
        self.transport = transport

    def get_json(self, operation: str, path: str) -> dict[str, Any] | None:
        """Devuelve el cuerpo JSON de un `200`, `None` en `404`.

        Raises:
            DependencyUnavailableError: En `401`/`403` (causa de denegación) y en
                tiempo agotado, error de red, `5xx`, otros estados o cuerpo no
                JSON (causa de indisponibilidad).
        """
        headers: dict[str, str] = {}

        if self.authorization:
            headers["Authorization"] = self.authorization

        trace_id = current_trace_id()

        if trace_id:
            headers["traceparent"] = build_traceparent(trace_id)

        started = time.perf_counter()

        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = client.get(f"{self.base_url}{path}", headers=headers)

        except httpx.HTTPError as exc:
            raise self._unavailable(
                operation,
                started,
                cause=self.unavailable_cause,
                outcome=type(exc).__name__,
                level=logging.ERROR,
            ) from None

        if response.status_code == 404:
            return None

        if response.status_code in {401, 403}:
            raise self._unavailable(
                operation,
                started,
                cause=self.denied_cause,
                outcome=f"estado={response.status_code}",
                level=logging.WARNING,
            )

        if response.status_code != 200:
            raise self._unavailable(
                operation,
                started,
                cause=self.unavailable_cause,
                outcome=f"estado={response.status_code}",
                level=logging.ERROR,
            )

        try:
            body = response.json()
        except ValueError:
            body = None

        if not isinstance(body, dict):
            raise self._unavailable(
                operation,
                started,
                cause=self.unavailable_cause,
                outcome="cuerpo_inesperado",
                level=logging.ERROR,
            )

        return body

    def unexpected_body(self, operation: str) -> DependencyUnavailableError:
        """Error para un `200` cuyo cuerpo no trae los campos del contrato."""
        logger.error(
            "Respuesta inesperada de dependencia causa=%s proveedor=%s operacion=%s "
            "resultado=cuerpo_inesperado",
            self.unavailable_cause,
            self.provider,
            operation,
        )
        return DependencyUnavailableError(
            provider=self.provider,
            cause=self.unavailable_cause,
            operation=operation,
        )

    def _unavailable(
        self,
        operation: str,
        started: float,
        *,
        cause: str,
        outcome: str,
        level: int,
    ) -> DependencyUnavailableError:
        duration_ms = round((time.perf_counter() - started) * 1000)
        logger.log(
            level,
            "No fue posible validar contra la dependencia causa=%s proveedor=%s "
            "operacion=%s resultado=%s duracion_ms=%s",
            cause,
            self.provider,
            operation,
            outcome,
            duration_ms,
        )
        return DependencyUnavailableError(
            provider=self.provider,
            cause=cause,
            operation=operation,
        )
