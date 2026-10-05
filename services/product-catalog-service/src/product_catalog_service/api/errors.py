"""Traducción de errores a Problem Details (RFC 9457) con `code` y `trace_id` (D3).

Regla D11 provisional (`contracts/errors.md`):

- `400`: cuerpo JSON ilegible o parámetro de ruta/consulta no interpretable.
- `422`: validación de campos y reglas de negocio de la entrada.
- `409`: unicidad, colisión y versión; `404`: recurso de la ruta inexistente;
  `503`: dependencia no disponible.

Base de datos propia no disponible (Constitución 2.4.0, Principio X; feature 009):
solo la pérdida o indisponibilidad de la conexión con PostgreSQL
(`is_database_unavailable`) se traduce a `503 DEPENDENCY_UNAVAILABLE` con
`dependency: database`; cualquier otro error de PostgreSQL (deadlock,
serialización, cancelación, bloqueo) conserva su respuesta `500`.

Los errores no controlados (`500 INTERNAL_ERROR`) los atiende `api/tracing.py`,
dentro del contexto de la solicitud, para que lleven el `trace_id`.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException

from product_catalog_service.application.exceptions import CODE_PREFIX, DomainError

PROBLEM_MEDIA_TYPE = "application/problem+json"
DATABASE_UNAVAILABLE_DETAIL = (
    "La base de datos del servicio no está disponible temporalmente. Intente de nuevo más tarde."
)
_DISCONNECT_SQLSTATES = frozenset({"57P01", "57P02", "57P03"})

# Mismo logger que `api/tracing.py`: el registro lleva el `trace_id`.
logger = logging.getLogger("product_catalog_service")
IMMUTABLE_FIELD_ERROR = "immutable_field"

_HTTP_CODES = {
    400: ("MALFORMED_REQUEST", "Solicitud mal formada"),
    401: ("UNAUTHENTICATED", "No autenticado"),
    403: ("FORBIDDEN", "Acceso denegado"),
    404: ("NOT_FOUND", "Recurso no encontrado"),
    405: ("METHOD_NOT_ALLOWED", "Método no permitido"),
    409: ("CONFLICT", "Conflicto"),
}


def is_database_unavailable(exc: Exception) -> bool:
    """Indica si el error es la pérdida o indisponibilidad de la conexión con PostgreSQL.

    `True` para `InterfaceError` (conexión cerrada) y para `OperationalError`
    con la conexión invalidada por SQLAlchemy, sin SQLSTATE (el servidor no
    respondió: conexión rechazada, host sin resolver, tiempo agotado,
    conexión perdida), con SQLSTATE de clase `08` o `57P01`/`57P02`/`57P03`.
    `False` para todo lo demás (p. ej. deadlock `40P01`, serialización
    `40001`, cancelación `57014`, bloqueo `55P03`).
    """
    if isinstance(exc, InterfaceError):
        return True

    if not isinstance(exc, OperationalError):
        return False

    if exc.connection_invalidated:
        return True

    sqlstate = getattr(exc.orig, "sqlstate", None)
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
    slug = code.lower().replace("_", "-")
    body: dict[str, Any] = {
        "type": f"https://sio/errors/product-catalog/{slug}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": f"{CODE_PREFIX}{code}",
        "trace_id": getattr(request.state, "trace_id", None),
    }
    if extra:
        body.update(extra)

    return JSONResponse(
        status_code=status,
        content=body,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=headers,
    )


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = [str(part) for part in loc[1:]] if len(loc) > 1 else [str(part) for part in loc]
    return ".".join(parts)


async def _handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    return problem_response(
        request,
        status=exc.status_code,
        code=exc.code,
        title=exc.title,
        detail=exc.detail,
        extra=exc.extra,
    )


async def _handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()

    malformed = [
        error
        for error in errors
        if error.get("type") == "json_invalid"
        or (error.get("loc") and error["loc"][0] in {"query", "path"})
    ]
    if malformed:
        return problem_response(
            request,
            status=400,
            code="MALFORMED_REQUEST",
            title="Solicitud mal formada",
            detail="El cuerpo o los parámetros de la solicitud no pueden interpretarse.",
            extra={
                "errors": [
                    {
                        "field": _field_name(tuple(error.get("loc", ()))),
                        "message": error.get("msg", ""),
                        "code": "MALFORMED_REQUEST",
                    }
                    for error in malformed
                ]
            },
        )

    immutable = [error for error in errors if error.get("type") == IMMUTABLE_FIELD_ERROR]
    code = "IMMUTABLE_FIELD" if immutable else "VALIDATION_ERROR"
    title = "Campo inmutable" if immutable else "Solicitud inválida"

    return problem_response(
        request,
        status=422,
        code=code,
        title=title,
        detail="La solicitud contiene datos inválidos.",
        extra={
            "errors": [
                {
                    "field": _field_name(tuple(error.get("loc", ()))),
                    "message": error.get("msg", ""),
                    "code": "IMMUTABLE_FIELD"
                    if error.get("type") == IMMUTABLE_FIELD_ERROR
                    else "VALIDATION_ERROR",
                }
                for error in errors
            ]
        },
    )


async def _handle_http_exception(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
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


async def _handle_stale_data(request: Request, exc: StaleDataError) -> JSONResponse:
    return problem_response(
        request,
        status=409,
        code="VERSION_CONFLICT",
        title="Versión desactualizada",
        detail="El registro fue modificado por otra operación; consulte la versión vigente.",
    )


async def _handle_database_unavailable(request: Request, exc: Exception) -> JSONResponse:
    if not is_database_unavailable(exc):
        # Otro error de PostgreSQL: conserva su respuesta (500 en `tracing.py`).
        raise exc

    orig = getattr(exc, "orig", exc)
    logger.warning(
        "PostgreSQL no disponible metodo=%s ruta=%s causa=%s sqlstate=%s",
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
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(StaleDataError, _handle_stale_data)
    app.add_exception_handler(OperationalError, _handle_database_unavailable)
    app.add_exception_handler(InterfaceError, _handle_database_unavailable)
