"""Middleware de trazabilidad de solicitudes (`trace_id`, D14 provisional).

Es el middleware más externo de la aplicación:

- toma el trace-id de `traceparent` (W3C) si es válido o genera uno nuevo;
- lo guarda en `scope["state"]["trace_id"]` y en el contexto de logs;
- devuelve la cabecera `X-Trace-Id` en toda respuesta;
- convierte a Problem Details los `401` que emite `sio-auth`, que responde
  con `{"detail": ...}` antes de llegar a los manejadores de errores;
- responde `500 INTERNAL_ERROR` sin detalles ante errores no controlados.
"""

from __future__ import annotations

import json
import logging
import re
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from operational_context_service.api.errors import CODE_PREFIX, ERROR_TYPE_BASE
from operational_context_service.observability import (
    SERVICE_LOGGER,
    reset_trace_id,
    set_trace_id,
)

TRACE_HEADER = "x-trace-id"
logger = logging.getLogger(SERVICE_LOGGER)
_TRACEPARENT = re.compile(r"^[0-9a-f]{2}-([0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")


def _extract_trace_id(scope: Scope) -> str:
    for key, value in scope.get("headers", []):
        if key.lower() == b"traceparent":
            match = _TRACEPARENT.match(value.decode("latin-1").strip().lower())
            if match and match.group(1) != "0" * 32:
                return match.group(1)
    return uuid4().hex


class TracingMiddleware:
    """Middleware ASGI de trazabilidad y normalización de respuestas 401."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        trace_id = _extract_trace_id(scope)
        scope.setdefault("state", {})["trace_id"] = trace_id
        token = set_trace_id(trace_id)

        pending_start: Message | None = None
        buffered_body = bytearray()
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal pending_start, response_started

            if message["type"] == "http.response.start":
                response_started = True
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != TRACE_HEADER.encode()
                ]
                headers.append((TRACE_HEADER.encode(), trace_id.encode()))
                message = {**message, "headers": headers}

                if message["status"] == 401 and not _is_problem(headers):
                    pending_start = message
                    return

                await send(message)
                return

            if message["type"] == "http.response.body" and pending_start is not None:
                buffered_body.extend(message.get("body", b""))
                if message.get("more_body", False):
                    return

                body = _problem(
                    scope,
                    trace_id,
                    status=401,
                    code="UNAUTHENTICATED",
                    title="No autenticado",
                    detail=_original_detail(bytes(buffered_body))
                    or "Se requiere un token de acceso válido.",
                )
                headers = [
                    (key, value)
                    for key, value in pending_start["headers"]
                    if key.lower() not in {b"content-type", b"content-length"}
                ]
                headers.append((b"content-type", b"application/problem+json"))
                headers.append((b"content-length", str(len(body)).encode()))
                await send({**pending_start, "headers": headers})
                await send({"type": "http.response.body", "body": body})
                pending_start = None
                return

            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)

        except Exception:
            # Los errores no controlados se registran y responden aquí, dentro
            # del contexto de la solicitud, para que lleven el trace_id (D3).
            logger.exception("Error no controlado")
            if response_started:
                raise
            body = _problem(
                scope,
                trace_id,
                status=500,
                code="INTERNAL_ERROR",
                title="Error interno",
                detail="Ocurrió un error inesperado. Informe el trace_id al soporte.",
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/problem+json"),
                        (b"content-length", str(len(body)).encode()),
                        (TRACE_HEADER.encode(), trace_id.encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})

        finally:
            reset_trace_id(token)


def _is_problem(headers: list[tuple[bytes, bytes]]) -> bool:
    return any(
        key.lower() == b"content-type" and value.startswith(b"application/problem+json")
        for key, value in headers
    )


def _original_detail(original: bytes) -> str | None:
    try:
        parsed = json.loads(original or b"{}")
    except ValueError:
        return None

    if isinstance(parsed, dict) and isinstance(parsed.get("detail"), str):
        return parsed["detail"]

    return None


def _problem(
    scope: Scope,
    trace_id: str,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
) -> bytes:
    problem = {
        "type": f"{ERROR_TYPE_BASE}/{code.lower().replace('_', '-')}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": scope.get("path", ""),
        "code": f"{CODE_PREFIX}{code}",
        "trace_id": trace_id,
    }
    return json.dumps(problem, ensure_ascii=False).encode("utf-8")
