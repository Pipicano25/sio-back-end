"""Trazabilidad de solicitudes (`trace_id`, R-07, D14 provisional).

El middleware es el más externo de la aplicación:

- toma el trace-id de `traceparent` (W3C) si es válido o genera uno nuevo;
- lo guarda en `scope["state"]["trace_id"]` y en un `ContextVar` para los logs;
- devuelve la cabecera `X-Trace-Id` en toda respuesta;
- convierte los `401` que emite `sio-auth` a Problem Details (D3), porque esa
  librería responde con `{"detail": ...}` antes de llegar a los manejadores.

`configure_logging()` agrega el `trace_id` a todo registro de los loggers del
servicio y de uvicorn (D3: el `trace_id` también DEBE registrarse en los logs).
"""

from __future__ import annotations

import json
import logging
import re
import secrets
from contextvars import ContextVar
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

TRACE_HEADER = "x-trace-id"
logger = logging.getLogger("product_catalog_service")
_TRACEPARENT = re.compile(r"^[0-9a-f]{2}-([0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$")
_current_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def current_trace_id() -> str | None:
    """Trace-id de la solicitud en curso (para logs y llamadas salientes)."""
    return _current_trace_id.get()


NO_TRACE = "-"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] trace_id=%(trace_id)s %(message)s"
# `sio_auth` registra las denegaciones por permiso (el permiso no viaja en el `403`).
AUTH_LOGGER = "sio_auth"
TRACED_LOGGERS = ("product_catalog_service", AUTH_LOGGER, "uvicorn", "uvicorn.error", "uvicorn.access")


class TraceIdFilter(logging.Filter):
    """Copia el `trace_id` de la solicitud en curso en cada registro de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "trace_id", None):
            record.trace_id = current_trace_id() or NO_TRACE
        return True


def configure_logging() -> None:
    """Agrega el filtro y el formato con `trace_id` a los loggers del servicio y de uvicorn.

    Es idempotente: se puede llamar en cada `create_app()` sin duplicar filtros ni
    manejadores. Uvicorn configura sus manejadores antes de importar la aplicación,
    así que aquí solo se les cambia el formato.
    """
    formatter = logging.Formatter(LOG_FORMAT)

    for name in TRACED_LOGGERS:
        logger = logging.getLogger(name)
        if not any(isinstance(item, TraceIdFilter) for item in logger.filters):
            logger.addFilter(TraceIdFilter())

        for handler in logger.handlers:
            if not any(isinstance(item, TraceIdFilter) for item in handler.filters):
                handler.addFilter(TraceIdFilter())
            handler.setFormatter(formatter)

    for name in ("product_catalog_service", AUTH_LOGGER):
        service_logger = logging.getLogger(name)
        if not service_logger.handlers:
            handler = logging.StreamHandler()
            handler.addFilter(TraceIdFilter())
            handler.setFormatter(formatter)
            service_logger.addHandler(handler)
            service_logger.setLevel(logging.INFO)


def build_traceparent(trace_id: str) -> str:
    """Construye una cabecera `traceparent` con un span nuevo."""
    return f"00-{trace_id}-{secrets.token_hex(8)}-01"


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
        token = _current_trace_id.set(trace_id)

        pending_start: Message | None = None
        buffered_body = bytearray()
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal pending_start

            if message["type"] == "http.response.start":
                nonlocal response_started
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

                body = _unauthorized_problem(bytes(buffered_body), scope, trace_id)
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
            # Los errores no controlados salen de la pila de middlewares antes de que
            # Starlette los atienda: se registran y responden aquí, dentro del contexto
            # de la solicitud, para que el log y la respuesta lleven el trace_id (D3).
            logger.exception("Error no controlado")
            if response_started:
                raise
            body = _internal_error_problem(scope, trace_id)
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
            _current_trace_id.reset(token)


def _is_problem(headers: list[tuple[bytes, bytes]]) -> bool:
    return any(
        key.lower() == b"content-type" and value.startswith(b"application/problem+json")
        for key, value in headers
    )


def _unauthorized_problem(original: bytes, scope: Scope, trace_id: str) -> bytes:
    detail = "Se requiere un token de acceso válido."
    try:
        parsed = json.loads(original or b"{}")
        if isinstance(parsed, dict) and isinstance(parsed.get("detail"), str):
            detail = parsed["detail"]
    except ValueError:
        pass

    problem = {
        "type": "https://sio/errors/product-catalog/unauthenticated",
        "title": "No autenticado",
        "status": 401,
        "detail": detail,
        "instance": scope.get("path", ""),
        "code": "PRODUCT_CATALOG.UNAUTHENTICATED",
        "trace_id": trace_id,
    }
    return json.dumps(problem, ensure_ascii=False).encode("utf-8")


def _internal_error_problem(scope: Scope, trace_id: str) -> bytes:
    problem = {
        "type": "https://sio/errors/product-catalog/internal-error",
        "title": "Error interno",
        "status": 500,
        "detail": "Ocurrió un error inesperado. Informe el trace_id al soporte.",
        "instance": scope.get("path", ""),
        "code": "PRODUCT_CATALOG.INTERNAL_ERROR",
        "trace_id": trace_id,
    }
    return json.dumps(problem, ensure_ascii=False).encode("utf-8")
