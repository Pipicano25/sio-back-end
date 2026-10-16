"""Configuración OpenAPI de Sales Service."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

TAG_SALES = "Ventas y líneas"
TAG_OPERATIONS = "Confirmación, anulación y operaciones"
TAG_SEQUENCES = "Secuencias de numeración"

OPENAPI_TAGS = [
    {"name": "health"},
    {
        "name": TAG_SALES,
        "description": (
            "Ventas en borrador con hasta 100 líneas. Solo **usuarios humanos**: una cuenta de servicio recibe "
            "`403`. Escribir exige el permiso, membresía `ACTIVE` y asignación `ACTIVE` a la sucursal de la venta; "
            "leer, el permiso y la membresía. Referencia inexistente o no resoluble → `422`; existente pero no apta "
            "→ `409`. Costo y margen solo con `perm:sales:sales:read-profitability`; sin él se omiten. Spec 020: "
            "solo contado; `payment_method_id` obligatorio (un único medio de pago activo de Payment Reference, "
            "declarativo: no registra pagos); sin descuentos (`discount_amount` solo admite `0`, "
            "`DISCOUNT_NOT_ALLOWED`). Spec 021 (provisional): sin impuesto adicional (`tax_amount` solo admite `0`, "
            "`TAX_NOT_ALLOWED`); el precio de la lista es el importe final que paga el cliente. **No es una solución "
            "fiscal**: no separa el impuesto incluido ni factura electrónicamente."
        ),
    },
    {
        "name": TAG_OPERATIONS,
        "description": (
            "Confirmar vuelve a verificar precios (`409 PRICES_CHANGED`) y existencias, descuenta el inventario "
            "(cantidad en unidad base), guarda el costo FIFO que informa Inventory y el margen, fija la fecha del "
            "día y asigna el número del período; anular revierte exactamente esa salida. Exigen "
            "`Idempotency-Key`: repetir la clave devuelve el mismo resultado sin duplicar movimientos. Con "
            "Inventory no disponible la operación queda `PENDING` y se completa con el reintento o el conciliador. "
            "Solo hay existencias de compras **recibidas** (spec 020): una compra confirmada sin recibir no permite "
            "vender (`409 INSUFFICIENT_STOCK`)."
        ),
    },
    {
        "name": TAG_SEQUENCES,
        "description": (
            "Numeración por empresa o sucursal con contador independiente por período (`NEVER`, año o año-mes "
            "según la fecha de la venta). A lo sumo una activa por empresa, sucursal y tipo."
        ),
    },
]

PROBLEM = {"application/problem+json": {"schema": {"type": "object"}}}


def problem(description: str) -> dict[str, Any]:
    return {"description": description, "content": PROBLEM}


READ_RESPONSES = {
    403: problem("`SALES.FORBIDDEN` o `SALES.OPERATIONAL_ACCESS_DENIED`."),
    404: problem("`SALES.NOT_FOUND`: empresa fuera del alcance del usuario o recurso inexistente."),
}

WRITE_RESPONSES = {
    403: problem(
        "`SALES.FORBIDDEN` (sin permiso o cuenta de servicio), `SALES.BRANCH_ACCESS_DENIED` o "
        "`SALES.OPERATIONAL_ACCESS_DENIED`."
    ),
    404: problem("`SALES.NOT_FOUND`."),
    409: problem(
        "`SALES.REFERENCES_NOT_ELIGIBLE`, `SALES.VERSION_CONFLICT`, `SALES.INVALID_STATUS`, "
        "`SALES.OPERATION_IN_PROGRESS`."
    ),
    422: problem("`SALES.VALIDATION_ERROR` (`errors[].code`)."),
}

OPERATION_RESPONSES = {
    **WRITE_RESPONSES,
    409: problem(
        "`SALES.IDEMPOTENCY_KEY_CONFLICT`, `SALES.REFERENCES_NOT_ELIGIBLE`, `SALES.SEQUENCE_NOT_CONFIGURED`, "
        "`SALES.SEQUENCE_EXHAUSTED`, `SALES.PRICES_CHANGED`, `SALES.INSUFFICIENT_STOCK`, `SALES.INVENTORY_REJECTED`, "
        "`SALES.OPERATION_IN_PROGRESS`, `SALES.OPERATION_NOT_APPLIED`, `SALES.VERSION_CONFLICT`, "
        "`SALES.INVALID_STATUS`."
    ),
    422: problem("`SALES.VALIDATION_ERROR` o `SALES.SALE_WITHOUT_LINES`."),
}

SEQUENCE_RESPONSES = {
    403: problem("`SALES.FORBIDDEN` o `SALES.OPERATIONAL_ACCESS_DENIED`."),
    404: problem("`SALES.NOT_FOUND`."),
    409: problem(
        "`SALES.SEQUENCE_ALREADY_ACTIVE`, `SALES.SEQUENCE_IN_USE`, `SALES.VERSION_CONFLICT` o "
        "`SALES.REFERENCES_NOT_ELIGIBLE`."
    ),
    422: problem("`SALES.VALIDATION_ERROR`."),
}

_USER_RESPONSES = {
    "401": "Sin token o token inválido: `SALES.UNAUTHENTICATED`.",
    "503": (
        "`SALES.DEPENDENCY_UNAVAILABLE`: la extensión `dependency` indica cuál (`database`, "
        "`operational-context`, `commercial-relationship`, `product-catalog`, `party-identity`, "
        "`inventory`, `keycloak`)."
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
