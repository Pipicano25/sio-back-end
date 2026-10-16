"""Configuración OpenAPI de Purchase Service."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

TAG_PURCHASES = "Compras y líneas"
TAG_OPERATIONS = "Confirmación, anulación y operaciones"
TAG_EVENTS = "Hitos logísticos"
TAG_SEQUENCES = "Secuencias de numeración"

OPENAPI_TAGS = [
    {"name": "health"},
    {
        "name": TAG_PURCHASES,
        "description": (
            "Compras en borrador con hasta 100 líneas. Solo **usuarios humanos**: una cuenta de servicio recibe "
            "`403`. Escribir exige el permiso, membresía `ACTIVE` y asignación `ACTIVE` a la sucursal de la compra; "
            "leer, el permiso y la membresía. Referencia inexistente o no resoluble → `422`; existente pero no apta "
            "→ `409`."
        ),
    },
    {
        "name": TAG_OPERATIONS,
        "description": (
            "Confirmar asigna el número del período y deja la compra pendiente de recepción; la **recepción física** "
            "ingresa la mercancía en Inventory (cantidad en unidad base, costo por unidad base sin impuestos) y "
            "registra el costo para la actualización automática de precios (spec 021). Anular una compra recibida "
            "revierte exactamente su entrada. Exigen "
            "`Idempotency-Key`: repetir la clave devuelve el mismo resultado sin duplicar movimientos. Con "
            "Inventory no disponible la operación queda `PENDING` y se completa con el reintento o el conciliador."
        ),
    },
    {
        "name": TAG_EVENTS,
        "description": (
            "Hitos inmutables `ORDERED → SUPPLIER_DISPATCHED → ARRIVED → RECEIVED → AVAILABLE_FOR_SALE`. Un "
            "error se corrige registrando otro hito del mismo tipo, que pasa a ser el vigente."
        ),
    },
    {
        "name": TAG_SEQUENCES,
        "description": (
            "Numeración por empresa o sucursal con contador independiente por período (`NEVER`, año o año-mes "
            "según la fecha de la compra). A lo sumo una activa por empresa, sucursal y tipo."
        ),
    },
]

PROBLEM = {"application/problem+json": {"schema": {"type": "object"}}}


def problem(description: str) -> dict[str, Any]:
    return {"description": description, "content": PROBLEM}


READ_RESPONSES = {
    403: problem("`PURCHASE.FORBIDDEN` o `PURCHASE.OPERATIONAL_ACCESS_DENIED`."),
    404: problem("`PURCHASE.NOT_FOUND`: empresa fuera del alcance del usuario o recurso inexistente."),
}

WRITE_RESPONSES = {
    403: problem(
        "`PURCHASE.FORBIDDEN` (sin permiso o cuenta de servicio), `PURCHASE.BRANCH_ACCESS_DENIED` o "
        "`PURCHASE.OPERATIONAL_ACCESS_DENIED`."
    ),
    404: problem("`PURCHASE.NOT_FOUND`."),
    409: problem(
        "`PURCHASE.REFERENCES_NOT_ELIGIBLE`, `PURCHASE.VERSION_CONFLICT`, `PURCHASE.INVALID_STATUS`, "
        "`PURCHASE.OPERATION_IN_PROGRESS`, `PURCHASE.EVENT_NOT_ALLOWED_IN_STATUS`, "
        "`PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE` (la presentación ya está en otra línea, spec 021)."
    ),
    422: problem("`PURCHASE.VALIDATION_ERROR` (`errors[].code`)."),
}

OPERATION_RESPONSES = {
    **WRITE_RESPONSES,
    409: problem(
        "`PURCHASE.IDEMPOTENCY_KEY_CONFLICT`, `PURCHASE.REFERENCES_NOT_ELIGIBLE`, `PURCHASE.SEQUENCE_NOT_CONFIGURED`, "
        "`PURCHASE.SEQUENCE_EXHAUSTED`, `PURCHASE.INVENTORY_REJECTED`, `PURCHASE.INVENTORY_ALREADY_CONSUMED`, "
        "`PURCHASE.OPERATION_IN_PROGRESS`, `PURCHASE.OPERATION_NOT_APPLIED`, `PURCHASE.VERSION_CONFLICT`, "
        "`PURCHASE.INVALID_STATUS`; al confirmar (spec 021) `PURCHASE.PURCHASE_TAX_NOT_CONFIGURED`, "
        "`PURCHASE.PURCHASE_TAX_CHANGED` y `PURCHASE.DUPLICATE_PRESENTATION_IN_PURCHASE`."
    ),
    422: problem("`PURCHASE.VALIDATION_ERROR` o `PURCHASE.PURCHASE_WITHOUT_LINES`."),
}

SEQUENCE_RESPONSES = {
    403: problem("`PURCHASE.FORBIDDEN` o `PURCHASE.OPERATIONAL_ACCESS_DENIED`."),
    404: problem("`PURCHASE.NOT_FOUND`."),
    409: problem(
        "`PURCHASE.SEQUENCE_ALREADY_ACTIVE`, `PURCHASE.SEQUENCE_IN_USE`, `PURCHASE.VERSION_CONFLICT` o "
        "`PURCHASE.REFERENCES_NOT_ELIGIBLE`."
    ),
    422: problem("`PURCHASE.VALIDATION_ERROR`."),
}

_USER_RESPONSES = {
    "401": "Sin token o token inválido: `PURCHASE.UNAUTHENTICATED`.",
    "503": (
        "`PURCHASE.DEPENDENCY_UNAVAILABLE`: la extensión `dependency` indica cuál (`database`, "
        "`operational-context`, `commercial-relationship`, `product-catalog`, `party-identity`, "
        "`payment-reference`, `inventory`, `keycloak`)."
    ),
}


def configure_bearer_openapi(app: FastAPI, public_paths: Collection[str]) -> None:
    """Documenta HTTP Bearer en OpenAPI; la validación real la hace `sio-auth`."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title, version=app.version, description=app.description, routes=app.routes, tags=app.openapi_tags
        )
        components = schema.setdefault("components", {})
        components.setdefault("securitySchemes", {})["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Ingrese un Access Token válido emitido para SIO.",
        }

        for path, path_item in schema.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for operation in path_item.values():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue
                if path in public_paths:
                    operation["security"] = []
                else:
                    operation["security"] = [{"BearerAuth": []}]
                    for status_code, description in _USER_RESPONSES.items():
                        operation["responses"].setdefault(status_code, {"description": description, "content": PROBLEM})

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
