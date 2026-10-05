"""Traducción de errores a Problem Details (RFC 9457) con `code` y `trace_id` (D3).

Este módulo es el **único** que asigna estados HTTP (Principio XII): las
excepciones de aplicación solo llevan `code`, mensaje y campo, y la tabla
`_STATUS_BY_CODE` los traduce (`contracts/errors.md`).

Regla D11 provisional: `400` solo si el cuerpo JSON no se puede interpretar;
`422` para validación de entrada y de dominio, incluidas las referencias
externas inexistentes, inactivas o inválidas; `409` unicidad, versión y
transición; `404` recurso inexistente o fuera del alcance; `503` dependencia no
disponible, con la extensión `dependency`.

Base de datos propia no disponible (Constitución 2.4.0, Principio X; feature 009):
solo la pérdida o indisponibilidad de la conexión con PostgreSQL
(`is_database_unavailable`) se traduce a `503 DEPENDENCY_UNAVAILABLE` con
`dependency: database`; cualquier otro error de PostgreSQL (deadlock,
serialización, cancelación, bloqueo) conserva su respuesta `500`.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from commercial_relationship_service.application.exceptions import (
    CommercialRelationshipError,
    DependencyUnavailableError,
)
from commercial_relationship_service.observability import SERVICE_LOGGER

CODE_PREFIX = "COMMERCIAL_RELATIONSHIP."
ERROR_TYPE_BASE = "https://sio/errors/commercial-relationship"
PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(SERVICE_LOGGER)

DATABASE_UNAVAILABLE_DETAIL = (
    "La base de datos del servicio no está disponible temporalmente. Intente de nuevo más tarde."
)
_DISCONNECT_SQLSTATES = frozenset({"57P01", "57P02", "57P03"})

_STATUS_BY_CODE: dict[str, int] = {
    "FORBIDDEN": 403,
    "OPERATIONAL_ACCESS_DENIED": 403,
    "PARTY_IDENTITY_ACCESS_DENIED": 403,
    "NOT_FOUND": 404,
    "VALIDATION_ERROR": 422,
    "IMMUTABLE_FIELD": 422,
    "COMPANY_INACTIVE": 422,
    "CURRENCY_NOT_SUPPORTED": 422,
    "PRICE_SCALE_NOT_ALLOWED": 422,
    "INVENTORY_FLAGS_INVALID": 422,
    "GLOBAL_PRODUCT_NOT_FOUND": 422,
    "GLOBAL_PRODUCT_INACTIVE": 422,
    "GLOBAL_PRODUCT_NOT_ELIGIBLE": 422,
    "CUSTOMER_IDENTITY_MISMATCH": 422,
    "CONTACT_PERSON_NOT_ALLOWED": 422,
    "CONTACT_PERSON_INVALID": 422,
    "PERSON_IDENTITY_NOT_FOUND": 422,
    "PERSON_IDENTITY_INACTIVE": 422,
    "ORGANIZATION_IDENTITY_NOT_FOUND": 422,
    "ORGANIZATION_IDENTITY_INACTIVE": 422,
    "SELF_RELATIONSHIP_NOT_ALLOWED": 422,
    "BATCH_LIMIT_EXCEEDED": 422,
    # Fase B (specs/010-commercial-relationship-commercial-product/contracts/errors.md)
    "COMPANY_PRODUCT_NOT_FOUND": 422,
    "COMPANY_PRODUCT_INACTIVE": 422,
    "COMPANY_SUPPLIER_NOT_FOUND": 422,
    "COMPANY_SUPPLIER_INACTIVE": 422,
    "COMPANY_SUPPLIER_BLOCKED": 422,
    "PRESENTATION_NOT_FOUND": 422,
    "PRESENTATION_INACTIVE": 422,
    "PRESENTATION_OF_OTHER_PRODUCT": 422,
    "PRESENTATION_NOT_PURCHASABLE": 422,
    "PRESENTATION_NOT_SELLABLE": 422,
    "GLOBAL_PRESENTATION_NOT_FOUND": 422,
    "GLOBAL_PRESENTATION_INACTIVE": 422,
    "GLOBAL_PRESENTATION_NOT_ELIGIBLE": 422,
    "GLOBAL_PRESENTATION_OF_OTHER_PRODUCT": 422,
    "DEFAULT_FLAG_INVALID": 422,
    "DEFAULT_REQUIRES_ACTIVE": 422,
    "PURCHASE_UNIT_NOT_BASE_UNIT": 422,
    "PAYMENT_CONDITION_TYPE_NOT_FOUND": 422,
    "PAYMENT_CONDITION_TYPE_INACTIVE": 422,
    "PAYMENT_TERMS_INCONSISTENT": 422,
    "VALIDITY_INVALID": 422,
    "PRICE_LIST_NOT_FOUND": 422,
    "PRICE_LIST_INACTIVE": 422,
    "PRICE_IN_EFFECT_NOT_MODIFIABLE": 422,
    "PRICE_CHANGE_OUT_OF_PERIOD": 422,
    "DUPLICATE_PRESENTATION_ADOPTION": 409,
    "DUPLICATE_SKU": 409,
    "DUPLICATE_SUPPLIER_PRODUCT": 409,
    "DUPLICATE_PRICE_LIST_CODE": 409,
    "PRICE_PERIOD_OVERLAP": 409,
    "DUPLICATE_ADOPTION": 409,
    "DUPLICATE_CUSTOMER": 409,
    "DUPLICATE_SUPPLIER": 409,
    "DUPLICATE_INTERNAL_CODE": 409,
    "VERSION_CONFLICT": 409,
    "INVALID_STATUS_TRANSITION": 409,
    "DEPENDENCY_UNAVAILABLE": 503,
}

_HTTP_CODES = {
    400: ("MALFORMED_REQUEST", "Solicitud mal formada"),
    401: ("UNAUTHENTICATED", "No autenticado"),
    403: ("FORBIDDEN", "Acceso denegado"),
    404: ("NOT_FOUND", "Recurso no encontrado"),
    405: ("METHOD_NOT_ALLOWED", "Método no permitido"),
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


def status_for_code(code: str) -> int | None:
    """Estado HTTP de un `code` de aplicación, o `None` si no está mapeado."""
    return _STATUS_BY_CODE.get(code)


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

    return JSONResponse(
        status_code=status,
        content=body,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=headers,
    )


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = [str(part) for part in loc[1:]] if len(loc) > 1 else [str(part) for part in loc]
    return ".".join(parts)


async def _handle_application_error(
    request: Request,
    exc: CommercialRelationshipError,
) -> JSONResponse:
    status = status_for_code(exc.code)

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

    if exc.field:
        extra["errors"] = [
            {"field": exc.field, "message": exc.message, "code": exc.code},
        ]

    return problem_response(
        request,
        status=status,
        code=exc.code,
        title=exc.title,
        detail=exc.message,
        extra=extra or None,
    )


def _validation_message(error: dict[str, Any]) -> str:
    message = str(error.get("msg", ""))
    # Pydantic antepone "Value error, " a los ValueError de los validadores.
    return message.removeprefix("Value error, ")


async def _handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()

    if any(error.get("type") == "json_invalid" for error in errors):
        return problem_response(
            request,
            status=400,
            code="MALFORMED_REQUEST",
            title="Solicitud mal formada",
            detail="El cuerpo de la solicitud no es un JSON válido.",
        )

    immutable = [error for error in errors if error.get("type") == "immutable_field"]

    if immutable:
        return problem_response(
            request,
            status=422,
            code="IMMUTABLE_FIELD",
            title="Campo inmutable",
            detail="La solicitud intenta modificar campos inmutables.",
            extra={
                "errors": [
                    {
                        "field": _field_name(tuple(error.get("loc", ()))),
                        "message": _validation_message(error),
                        "code": "IMMUTABLE_FIELD",
                    }
                    for error in immutable
                ]
            },
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
                    "field": _field_name(tuple(error.get("loc", ()))),
                    "message": _validation_message(error),
                    "code": "VALIDATION_ERROR",
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
    app.add_exception_handler(CommercialRelationshipError, _handle_application_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(OperationalError, _handle_database_unavailable)
    app.add_exception_handler(InterfaceError, _handle_database_unavailable)
