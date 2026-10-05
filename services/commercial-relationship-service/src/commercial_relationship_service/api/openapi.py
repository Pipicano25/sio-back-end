"""Configuración OpenAPI de Commercial Relationship Service."""

from collections.abc import Collection
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def configure_bearer_openapi(
    app: FastAPI,
    public_paths: Collection[str],
) -> None:
    """Configura autenticación HTTP Bearer en OpenAPI.

    Esta configuración documenta el mecanismo Bearer para Swagger. La
    validación real del token continúa delegada en `sio-auth`.

    Args:
        app: Aplicación FastAPI.
        public_paths: Rutas públicas que no requieren Bearer.
    """

    def custom_openapi() -> dict[str, Any]:
        """Construye el esquema OpenAPI del servicio.

        Returns:
            Esquema OpenAPI con seguridad HTTP Bearer.
        """
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
        security_schemes = components.setdefault(
            "securitySchemes",
            {},
        )

        security_schemes["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Ingrese un Access Token válido emitido para SIO."
            ),
        }

        paths = schema.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue

                if "responses" not in operation:
                    continue

                if path in public_paths:
                    operation["security"] = []
                else:
                    operation["security"] = [{"BearerAuth": []}]
                    _document_user_responses(operation["responses"])

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi


TAG_PRICE_LISTS = "Listas de precios (definir las listas)"
TAG_PRICE_LIST_ITEMS = "Precios por producto dentro de una lista"
TAG_APPLICABLE_PRICES = "Consultar el precio que aplica a una venta"

# Secciones de /docs en el orden de registro de los routers; las de precios llevan una descripción
# que explica en qué se diferencian.
OPENAPI_TAGS = [
    {"name": "health"},
    {"name": "Productos empresariales"},
    {"name": "Clientes"},
    {"name": "Proveedores"},
    {"name": "Resumen de empresas"},
    {"name": "Presentaciones empresariales"},
    {"name": "Productos de proveedor"},
    {"name": "Condiciones de pago del proveedor"},
    {
        "name": TAG_PRICE_LISTS,
        "description": (
            "Crea y administra las **listas** de la empresa (p. ej. *Minorista*, *Mayorista*), cada una con "
            "su moneda, su vigencia y, si se desea, marcada como predeterminada. Aquí no se registran "
            "precios: una lista es solo el contenedor (`price_lists`)."
        ),
    },
    {
        "name": TAG_PRICE_LIST_ITEMS,
        "description": (
            "Registra **cuánto vale** un producto (o una presentación) dentro de una lista y desde cuándo "
            "hasta cuándo rige ese valor. Guarda el historial: un precio en vigencia no se edita, se "
            "cambia con `change-price` (`price_list_items`)."
        ),
    },
    {
        "name": TAG_APPLICABLE_PRICES,
        "description": (
            "**Solo consulta, no guarda nada.** Dadas hasta 100 líneas (producto, presentación opcional y "
            "lista opcional) y un instante, responde qué precio usar: el de la lista indicada o la "
            "predeterminada; si no hay lista aplicable, el `sale_price` del producto empresarial. Lo "
            "usarán Ventas y Compras al armar un documento."
        ),
    },
]


_PROBLEM = {"application/problem+json": {"schema": {"type": "object"}}}

# Respuestas transversales de toda ruta de usuario (`contracts/rest-api.md`, reglas generales).
_USER_RESPONSES = {
    "401": "Sin token o token inválido: `COMMERCIAL_RELATIONSHIP.UNAUTHENTICATED`.",
    "403": (
        "`COMMERCIAL_RELATIONSHIP.FORBIDDEN`: falta el permiso de la operación. "
        "`COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED`: Operational Context respondió `403` al "
        "evaluar el acceso operativo del usuario (FR-052; no aplica a la exención técnica). "
        "`COMMERCIAL_RELATIONSHIP.PARTY_IDENTITY_ACCESS_DENIED`: Party Identity respondió `403` al "
        "validar una identidad (FR-054)."
    ),
    "404": "`COMMERCIAL_RELATIONSHIP.NOT_FOUND`: recurso inexistente o fuera del alcance del usuario (FR-041).",
    "503": (
        "`COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE`: un proveedor no está disponible; la extensión "
        "`dependency` indica cuál (`operational-context`, `product-catalog`, `party-identity`)."
    ),
}


def _document_user_responses(responses: dict[str, Any]) -> None:
    """Documenta en una operación protegida las respuestas transversales de la API."""
    for status_code, description in _USER_RESPONSES.items():
        responses.setdefault(status_code, {"description": description, "content": _PROBLEM})
