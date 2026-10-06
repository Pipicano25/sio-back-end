"""Traducción de errores a Problem Details (RFC 9457) con `code` y `trace_id` (D3).

Único módulo que asigna estados HTTP (Principio XII; `contracts/errors.md`).
Regla D11 provisional: `400` solo si el cuerpo JSON no se puede interpretar;
`422` formato y referencias; `409` conflictos con el estado; `404` inexistente o
fuera del alcance; `503` dependencia no disponible con la extensión `dependency`.

La base propia no disponible (Principio X) y el `lock_timeout` agotado o un
interbloqueo (R-04) se traducen a `503 DEPENDENCY_UNAVAILABLE` con
`dependency: database`; cualquier otro error de PostgreSQL conserva su `500`.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from inventory_service.application.exceptions import DependencyUnavailableError, InventoryError
from inventory_service.observability import SERVICE_LOGGER

CODE_PREFIX = "INVENTORY."
ERROR_TYPE_BASE = "https://sio/errors/inventory"
PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(SERVICE_LOGGER)

DATABASE_UNAVAILABLE_DETAIL = (
    "La base de datos del servicio no está disponible temporalmente. Intente de nuevo más tarde."
)
_DISCONNECT_SQLSTATES = frozenset({"57P01", "57P02", "57P03"})
_RETRYABLE_LOCK_SQLSTATES = frozenset({"55P03", "40P01"})
"""`lock_not_available` (lock_timeout agotado) y `deadlock_detected`."""

_STATUS_BY_CODE: dict[str, int] = {
    "VALIDATION_ERROR": 422,
    "OPERATION_KEY_CONFLICT": 409,
    "INSUFFICIENT_STOCK": 409,
    "ALREADY_REVERSED": 409,
    "REVERSAL_NOT_ALLOWED": 409,
    "NOT_FOUND": 404,
    "OPERATIONAL_ACCESS_DENIED": 403,
    "DEPENDENCY_UNAVAILABLE": 503,
}

_HTTP_CODES = {
    400: ("MALFORMED_BODY", "Solicitud mal formada"),
    401: ("UNAUTHENTICATED", "No autenticado"),
    403: ("FORBIDDEN", "Acceso denegado"),
    404: ("NOT_FOUND", "Recurso no encontrado"),
    405: ("METHOD_NOT_ALLOWED", "Método no permitido"),
}

VALIDATION_CAUSES = frozenset(
    {
        "REQUIRED",
        "INVALID_FORMAT",
        "UNKNOWN_FIELD",
        "LINES_OUT_OF_RANGE",
        "DUPLICATE_ORIGIN_DETAIL",
        "QUANTITY_NOT_POSITIVE",
        "TOO_MANY_DECIMALS",
        "QUANTITY_OUT_OF_RANGE",
        "UNIT_COST_NOT_ALLOWED",
        "UNIT_COST_NEGATIVE",
        "ORIGIN_TYPE_MISMATCH",
        "REASON_REQUIRED",
        "INVALID_DATE_RANGE",
        "PAGE_SIZE_OUT_OF_RANGE",
    }
)
"""Causas de `errors[].code` que pueden venir de la validación de esquemas."""


def is_database_unavailable(exc: Exception) -> bool:
    """Indica si el error es la pérdida o indisponibilidad de PostgreSQL o un bloqueo agotado."""
    if isinstance(exc, InterfaceError):
        return True

    if not isinstance(exc, DBAPIError):
        return False

    sqlstate = getattr(exc.orig, "sqlstate", None)

    if sqlstate in _RETRYABLE_LOCK_SQLSTATES:
        return True

    if not isinstance(exc, OperationalError):
        return False

    if exc.connection_invalidated:
        return True

    return sqlstate is None or sqlstate.startswith("08") or sqlstate in _DISCONNECT_SQLSTATES


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
    """Ruta de un campo de la solicitud: `lines[3].quantity`, `page_size`."""
    parts = loc[1:] if len(loc) > 1 and loc[0] in {"body", "query", "path"} else loc
    path = ""

    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else str(part)

    return path


async def _handle_application_error(request: Request, exc: InventoryError) -> JSONResponse:
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

    extra: dict[str, Any] = dict(exc.context)

    if isinstance(exc, DependencyUnavailableError):
        # La causa real queda en el log con el trace_id; nunca en la respuesta.
        logger.warning(
            "Dependencia no disponible proveedor=%s operacion=%s causa=%s",
            exc.provider,
            exc.operation,
            exc.cause,
        )
        extra["dependency"] = exc.provider

    if exc.errors:
        extra["errors"] = list(exc.errors)

    logger.info("Solicitud rechazada codigo=%s estado=%s ruta=%s", exc.code, status, request.url.path)
    return problem_response(
        request, status=status, code=exc.code, title=exc.title, detail=exc.message, extra=extra or None
    )


def _validation_code(error: dict[str, Any]) -> str:
    error_type = str(error.get("type", ""))

    if error_type in VALIDATION_CAUSES:
        return error_type

    if error_type == "missing":
        return "REQUIRED"

    if error_type == "extra_forbidden":
        return "UNKNOWN_FIELD"

    return "INVALID_FORMAT"


def _validation_message(error: dict[str, Any]) -> str:
    return str(error.get("msg", "")).removeprefix("Value error, ")


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()

    if any(error.get("type") == "json_invalid" for error in errors):
        return problem_response(
            request,
            status=400,
            code="MALFORMED_BODY",
            title="Solicitud mal formada",
            detail="El cuerpo de la solicitud no es un JSON válido.",
        )

    return problem_response(
        request,
        status=422,
        code="VALIDATION_ERROR",
        title="Solicitud inválida",
        detail="La solicitud contiene datos inválidos.",
        extra={
            "errors": [
                {
                    "field": field_path(tuple(error.get("loc", ()))),
                    "message": _validation_message(error),
                    "code": _validation_code(error),
                }
                for error in errors
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


async def _handle_database_error(request: Request, exc: Exception) -> JSONResponse:
    if not is_database_unavailable(exc):
        raise exc

    orig = getattr(exc, "orig", exc)
    logger.warning(
        "PostgreSQL no disponible o bloqueo agotado metodo=%s ruta=%s causa=%s sqlstate=%s",
        request.method,
        request.url.path,
        type(orig).__name__,
        getattr(orig, "sqlstate", None),
    )
    return problem_response(
        request,
        status=503,
        code="DEPENDENCY_UNAVAILABLE",
        title="Dependencia no disponible",
        detail=DATABASE_UNAVAILABLE_DETAIL,
        extra={"dependency": "database"},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Registra los manejadores de errores en la aplicación."""
    app.add_exception_handler(InventoryError, _handle_application_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(DBAPIError, _handle_database_error)
    app.add_exception_handler(InterfaceError, _handle_database_error)
