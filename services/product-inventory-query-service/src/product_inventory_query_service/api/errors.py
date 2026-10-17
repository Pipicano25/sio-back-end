"""Traducción de errores a Problem Details (RFC 9457) con `code` y `trace_id` (D3).

Único módulo que asigna estados HTTP (Principio XII; `contracts/product-inventory-query-api.md` §5).
Regla D11 provisional de la spec 022: `422` para parámetros inválidos o desconocidos y para cursores
inválidos. A diferencia de otros servicios, el `503` **no** incluye la extensión `dependency`: la
dependencia que falló solo se registra en el log (FR-022-71).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from product_inventory_query_service.application.exceptions import (
    DependencyUnavailableError,
    InvalidCursorError,
    QueryServiceError,
)
from product_inventory_query_service.observability import SERVICE_LOGGER

CODE_PREFIX = "PRODUCT_INVENTORY_QUERY."
ERROR_TYPE_BASE = "https://sio/errors/product-inventory-query"
PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(SERVICE_LOGGER)

_STATUS_BY_CODE: dict[str, int] = {
    "VALIDATION_ERROR": 422,
    "INVALID_CURSOR": 422,
    "NOT_FOUND": 404,
    "FORBIDDEN": 403,
    "DEPENDENCY_UNAVAILABLE": 503,
}

_HTTP_CODES = {
    400: ("MALFORMED_REQUEST", "Solicitud mal formada"),
    401: ("UNAUTHENTICATED", "No autenticado"),
    403: ("FORBIDDEN", "Acceso denegado"),
    404: ("NOT_FOUND", "Recurso no encontrado"),
    405: ("METHOD_NOT_ALLOWED", "Método no permitido"),
}


def problem_response(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    extra: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Construye una respuesta `application/problem+json`."""
    body: dict[str, Any] = {
        "type": f"{ERROR_TYPE_BASE}/{code.lower().replace('_', '-')}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": f"{CODE_PREFIX}{code}",
        "trace_id": getattr(request.state, "trace_id", None),
    }

    if extra:
        body.update(extra)

    return JSONResponse(status_code=status, content=body, media_type=PROBLEM_MEDIA_TYPE, headers=headers)


def field_path(loc: tuple[Any, ...]) -> str:
    """Ruta de un parámetro: `page_size`, `brand_id[1]`."""
    parts = loc[1:] if len(loc) > 1 and loc[0] in {"body", "query", "path"} else loc
    path = ""

    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else str(part)

    return path


async def _handle_application_error(request: Request, exc: QueryServiceError) -> JSONResponse:
    status = _STATUS_BY_CODE.get(exc.code)

    if status is None:
        logger.error("Código de error sin estado HTTP asignado: %s", exc.code)
        return problem_response(
            request,
            status=500,
            code="INTERNAL_ERROR",
            title="Error interno",
            detail="Ocurrió un error inesperado. Informe el trace_id al soporte.",
        )

    if isinstance(exc, DependencyUnavailableError):
        # La dependencia y la causa quedan en el log con el trace_id; nunca en la respuesta.
        logger.warning(
            "Dependencia no disponible proveedor=%s operacion=%s causa=%s", exc.provider, exc.operation, exc.cause
        )

    if isinstance(exc, InvalidCursorError):
        # Misma respuesta para malformado, firma inválida, otra empresa u otro endpoint (FR-022-149).
        logger.warning("Cursor rechazado causa=%s", exc.cause)

    extra: dict[str, Any] = dict(exc.context)

    if exc.errors:
        extra["errors"] = list(exc.errors)

    logger.info("Solicitud rechazada codigo=%s estado=%s ruta=%s", exc.code, status, request.url.path)
    return problem_response(
        request, status=status, code=exc.code, title=exc.title, detail=exc.message, extra=extra or None
    )


def _validation_code(error: dict[str, Any]) -> str:
    error_type = str(error.get("type", ""))

    if error_type == "missing":
        return "REQUIRED"

    if error_type == "extra_forbidden":
        return "UNKNOWN_FIELD"

    if error_type.isupper():
        return error_type

    return "INVALID_FORMAT"


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return problem_response(
        request,
        status=422,
        code="VALIDATION_ERROR",
        title="Solicitud inválida",
        detail="La solicitud contiene parámetros inválidos.",
        extra={
            "errors": [
                {
                    "field": field_path(tuple(error.get("loc", ()))),
                    "message": str(error.get("msg", "")).removeprefix("Value error, "),
                    "code": _validation_code(error),
                }
                for error in exc.errors()
            ]
        },
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, title = _HTTP_CODES.get(exc.status_code, ("HTTP_ERROR", "Error"))
    detail = exc.detail if isinstance(exc.detail, str) else title

    return problem_response(
        request,
        status=exc.status_code,
        code=code,
        title=title,
        detail=detail,
        headers=getattr(exc, "headers", None),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Registra los manejadores de errores en la aplicación."""
    app.add_exception_handler(QueryServiceError, _handle_application_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
