"""Apoyo de las pruebas de adaptadores con `httpx.MockTransport` (T015)."""

from __future__ import annotations

from collections.abc import Callable

import httpx

from purchase_service.infrastructure.keycloak_token_client import TokenUnavailableError


class Tokens:
    """Proveedor de token técnico: cuenta las renovaciones y puede fallar."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.issued = 0
        self.invalidated = 0

    def get_token(self) -> str:
        if self.fail:
            raise TokenUnavailableError("prueba")
        self.issued += 1
        return f"tecnico-{self.issued}"

    def invalidate(self) -> None:
        self.invalidated += 1


class Recorder:
    """Transporte que responde con `handler` y guarda cada solicitud."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.requests: list[httpx.Request] = []
        self._handler = handler
        self.transport = httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)


def json_response(status: int, body=None) -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(status, json=body if body is not None else {})


def expired_then(body) -> Callable[[httpx.Request], httpx.Response]:
    """Primera llamada `401` (token vencido); la segunda responde `200` con `body`."""
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        return httpx.Response(401) if state["calls"] == 1 else httpx.Response(200, json=body)

    return handler


def timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("tiempo agotado", request=request)
