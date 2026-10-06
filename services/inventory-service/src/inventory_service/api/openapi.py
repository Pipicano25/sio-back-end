"""Configuración OpenAPI de Inventory Service."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

TAG_ENTRIES = "Entradas de compra (cuentas de servicio)"
TAG_OUTPUTS = "Salidas de venta (cuentas de servicio)"
TAG_QUERIES = "Consulta de stock y kardex"

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
