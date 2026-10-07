"""Cliente HTTP común de las llamadas salientes (Principio XV).

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
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import httpx

from purchase_service.application.exceptions import DependencyUnavailableError
from purchase_service.infrastructure.keycloak_token_client import TokenUnavailableError, technical_dependency_error
from purchase_service.observability import (
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


class TechnicalCaller:
    """Llamada con el token técnico de Purchase y una renovación ante `401` (R-06)."""

    def __init__(self, client: HTTPDependencyClient, tokens: Any) -> None:
        self._client = client
        self._tokens = tokens

    @property
    def client(self) -> HTTPDependencyClient:
        return self._client

    def send(self, operation: str, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response: httpx.Response | None = None
        for attempt in range(2):
            try:
                token = self._tokens.get_token()
            except TokenUnavailableError:
                raise technical_dependency_error(self._client.provider, operation) from None

            response = self._client.send(operation, method, path, authorization=f"Bearer {token}", **kwargs)

            if response.status_code == 401 and attempt == 0:
                self._tokens.invalidate()
                continue

            return response

        assert response is not None
        return response

    def get_object(self, operation: str, path: str) -> dict[str, Any] | None:
        """`GET` técnico: `200` → objeto; `404` → `None`; cualquier otro → indisponible."""
        response = self.send(operation, "GET", path)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)

        if body is None:
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        return body

    def post_items(self, operation: str, path: str, ids: list[str]) -> list[dict[str, Any]]:
        """`POST …/batch-lookup` técnico: lista `items` del cuerpo (`200`)."""
        response = self.send(operation, "POST", path, json={"ids": ids})

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)
        items = body.get("items") if body else None

        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        return items


class UnexpectedBody(ValueError):
    """Campo ausente o con formato inesperado en la respuesta de un proveedor."""


def uuid_field(body: dict[str, Any], name: str, *, optional: bool = False) -> UUID | None:
    value = body.get(name)
    if value is None and optional:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        raise UnexpectedBody(name) from None


def text_field(body: dict[str, Any], name: str, *, optional: bool = False) -> str | None:
    value = body.get(name)
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise UnexpectedBody(name)
    return value


def bool_field(body: dict[str, Any], name: str) -> bool:
    value = body.get(name)
    if not isinstance(value, bool):
        raise UnexpectedBody(name)
    return value


def decimal_field(body: dict[str, Any], name: str, *, optional: bool = False) -> Decimal | None:
    value = body.get(name)
    if value is None and optional:
        return None
    if isinstance(value, bool) or value is None:
        raise UnexpectedBody(name)
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        raise UnexpectedBody(name) from None
    if not parsed.is_finite():
        raise UnexpectedBody(name)
    return parsed


def date_field(body: dict[str, Any], name: str, *, optional: bool = False) -> date | None:
    value = body.get(name)
    if value is None and optional:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise UnexpectedBody(name) from None


def int_field(body: dict[str, Any], name: str) -> int:
    value = body.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise UnexpectedBody(name)
    return value
