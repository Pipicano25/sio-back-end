"""Configuración OpenAPI de Inventory Service."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

TAG_ENTRIES = "Entradas de compra (cuentas de servicio)"
TAG_OUTPUTS = "Salidas de venta (cuentas de servicio)"
TAG_QUERIES = "Consulta de stock y kardex"
TAG_VALUATION = "Valoración FIFO"
TAG_ADJUSTMENTS = "Ajustes de inventario (usuarios asignados a la sucursal)"
TAG_COUNTS = "Conteos físicos (usuarios asignados a la sucursal)"
TAG_POLICIES = "Políticas de inventario"

OPENAPI_TAGS = [
    {"name": "health"},
    {
        "name": TAG_ENTRIES,
        "description": (
            "Purchase (y el cliente de pruebas) aplica entradas y sus reversos con su **identidad "
            "técnica**. Un token de usuario humano recibe `403` aunque tenga el permiso por comodín. "
            "Idempotente por `operation_key`; todo o nada; el reverso exige `company_id`."
        ),
    },
    {
        "name": TAG_OUTPUTS,
        "description": (
            "Sales (y el cliente de pruebas) aplica salidas y sus reversos con su identidad técnica. "
            "El saldo nunca queda negativo: una línea sin saldo rechaza toda la operación con "
            "`409 INSUFFICIENT_STOCK`."
        ),
    },
    {
        "name": TAG_QUERIES,
        "description": (
            "Saldo, stock de una sucursal, kardex y operaciones de **una empresa**: exige el permiso "
            "de lectura y membresía `ACTIVE` (Operational Context, con el token del usuario). Las "
            "cuentas de servicio con `perm:inventory:platform:lookup` consultan sin membresía."
        ),
    },
    {
        "name": TAG_VALUATION,
        "description": (
            "Valor del inventario por sucursal, capas FIFO y consumos de un movimiento. `cost_known = false` "
            "marca unidades de apertura sin costo histórico (distinto de un costo real 0). Mismo alcance por "
            "empresa que las consultas de stock."
        ),
    },
    {
        "name": TAG_ADJUSTMENTS,
        "description": (
            "Un **usuario humano** con el permiso, membresía `ACTIVE` y asignación `ACTIVE` a la sucursal "
            "registra un ajuste que se aplica en el acto (sin aprobación). Las cuentas de servicio reciben "
            "`403`. Idempotente por `adjustment_key` ligada al usuario."
        ),
    },
    {
        "name": TAG_COUNTS,
        "description": (
            "Ciclo `DRAFT → IN_PROGRESS → COMPLETED/CANCELLED` con `version`. Completar aplica todas las "
            "diferencias registradas como ajustes sobre el saldo vigente, todo o nada. Un conteo en curso por "
            "sucursal. Mismas reglas de acceso que los ajustes."
        ),
    },
    {
        "name": TAG_POLICIES,
        "description": (
            "Política de la empresa (una; solo `FIFO`; `is_active` solo de lectura) y niveles de reposición "
            "por producto y sucursal (una activa). Solo configuración: no generan compras ni movimientos. "
            "Escritura por usuarios humanos miembros con el permiso (comodín de administradores y supervisores)."
        ),
    },
]

PROBLEM = {"application/problem+json": {"schema": {"type": "object"}}}


def problem(description: str) -> dict[str, Any]:
    return {"description": description, "content": PROBLEM}


OPERATION_RESPONSES = {
    200: {"description": "La misma solicitud ya se había aplicado con esta clave (idempotente)."},
    400: problem("`INVENTORY.MALFORMED_BODY`: el cuerpo no es JSON interpretable."),
    409: problem(
        "`INVENTORY.OPERATION_KEY_CONFLICT` (clave usada con otra solicitud u otro cliente) o "
        "`INVENTORY.INSUFFICIENT_STOCK` (extensión `shortages`)."
    ),
    422: problem("`INVENTORY.VALIDATION_ERROR`: formato o referencia inválida (`errors[].code`)."),
}

REVERSAL_RESPONSES = {
    **OPERATION_RESPONSES,
    404: problem("`INVENTORY.NOT_FOUND`: la operación no existe en esa empresa o es de otro tipo."),
    409: problem(
        "`INVENTORY.ALREADY_REVERSED`, `INVENTORY.REVERSAL_NOT_ALLOWED`, `INVENTORY.INSUFFICIENT_STOCK` "
        "o `INVENTORY.OPERATION_KEY_CONFLICT`."
    ),
}

ADJUSTMENT_RESPONSES = {
    200: {"description": "La misma solicitud ya se había aplicado con esta clave (idempotente)."},
    400: problem("`INVENTORY.MALFORMED_BODY`: el cuerpo no es JSON interpretable."),
    403: problem(
        "`INVENTORY.FORBIDDEN` (sin permiso o cuenta de servicio), `INVENTORY.BRANCH_ACCESS_DENIED` (sin "
        "asignación activa a la sucursal, o sucursal o empresa inactiva) o `INVENTORY.OPERATIONAL_ACCESS_DENIED`."
    ),
    404: problem("`INVENTORY.NOT_FOUND`: la empresa o la sucursal están fuera del alcance del usuario."),
    409: problem("`INVENTORY.INSUFFICIENT_STOCK` (extensión `shortages`) o `INVENTORY.OPERATION_KEY_CONFLICT`."),
    422: problem(
        "`INVENTORY.VALIDATION_ERROR`: `UNIT_COST_REQUIRED`, `UNIT_COST_NOT_ALLOWED`, `REASON_REQUIRED`, "
        "producto no apto, `COMPANY_NOT_FOUND`."
    ),
}

COUNT_RESPONSES = {
    403: problem(
        "`INVENTORY.FORBIDDEN`, `INVENTORY.BRANCH_ACCESS_DENIED` o `INVENTORY.OPERATIONAL_ACCESS_DENIED`."
    ),
    404: problem("`INVENTORY.NOT_FOUND`: conteo, empresa o sucursal fuera del alcance del usuario."),
    409: problem(
        "`INVENTORY.COUNT_ALREADY_IN_PROGRESS`, `INVENTORY.COUNT_NOT_IN_PROGRESS`, "
        "`INVENTORY.INVALID_COUNT_TRANSITION`, `INVENTORY.VERSION_CONFLICT`, `INVENTORY.INSUFFICIENT_STOCK` "
        "(extensión `shortages`) o `INVENTORY.OPERATION_KEY_CONFLICT`."
    ),
    422: problem(
        "`INVENTORY.VALIDATION_ERROR`: `COUNT_WITHOUT_DETAILS`, `COUNT_DETAILS_LIMIT`, `UNIT_COST_REQUIRED` "
        "(`details[<company_product_id>].unit_cost`), `REASON_REQUIRED`, producto no apto."
    ),
}

POLICY_RESPONSES = {
    403: problem(
        "`INVENTORY.FORBIDDEN` (sin permiso, o cuenta de servicio al escribir) o "
        "`INVENTORY.OPERATIONAL_ACCESS_DENIED`."
    ),
    404: problem("`INVENTORY.NOT_FOUND`: empresa fuera del alcance o política inexistente."),
    409: problem(
        "`INVENTORY.POLICY_ALREADY_EXISTS`, `INVENTORY.ACTIVE_POLICY_EXISTS` o `INVENTORY.VERSION_CONFLICT`."
    ),
    422: problem(
        "`INVENTORY.VALIDATION_ERROR`: `VALUATION_METHOD_NOT_SUPPORTED`, `INVALID_LEVELS`, "
        "`INVALID_SERVICE_LEVEL`, `INVALID_WINDOW`, `UNKNOWN_FIELD` (`is_active`), sucursal o producto no aptos."
    ),
}

QUERY_RESPONSES = {
    403: problem(
        "`INVENTORY.FORBIDDEN` (falta el permiso de lectura) o `INVENTORY.OPERATIONAL_ACCESS_DENIED` "
        "(Operational Context negó la evaluación de la membresía)."
    ),
    404: problem("`INVENTORY.NOT_FOUND`: empresa fuera del alcance del usuario o recurso inexistente."),
}

_USER_RESPONSES = {
    "401": "Sin token o token inválido: `INVENTORY.UNAUTHENTICATED`.",
    "403": "`INVENTORY.FORBIDDEN`: falta el permiso de la operación (o no es una cuenta de servicio).",
    "503": (
        "`INVENTORY.DEPENDENCY_UNAVAILABLE`: la extensión `dependency` indica cuál "
        "(`database`, `operational-context`, `commercial-relationship`)."
    ),
}


def configure_bearer_openapi(app: FastAPI, public_paths: Collection[str]) -> None:
    """Documenta HTTP Bearer en OpenAPI; la validación real la hace `sio-auth`."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
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
