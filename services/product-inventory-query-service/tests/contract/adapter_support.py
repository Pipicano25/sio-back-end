"""Ayudas de las pruebas de contrato de los adaptadores (`httpx.MockTransport`)."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx

from product_inventory_query_service.infrastructure.http_client import AsyncDependencyClient, TechnicalCaller


class StaticTokens:
    def __init__(self) -> None:
        self.invalidated = 0

    async def token(self) -> str:
        return "token-tecnico"

    def invalidate(self) -> None:
        self.invalidated += 1


class Recorder:
    """Transporte que responde con `responder` y guarda cada solicitud."""

    def __init__(self, responder: Callable[[httpx.Request], httpx.Response]) -> None:
        self.responder = responder
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responder(request)

    def bodies(self) -> list[dict]:
        return [json.loads(request.content) for request in self.requests if request.content]


def dependency(provider: str, recorder: Recorder) -> AsyncDependencyClient:
    return AsyncDependencyClient(provider=provider, base_url=f"http://{provider}.test/api/v1", timeout_seconds=3,
                                 transport=httpx.MockTransport(recorder))


def technical(provider: str, recorder: Recorder) -> TechnicalCaller:
    return TechnicalCaller(dependency(provider, recorder), StaticTokens())
