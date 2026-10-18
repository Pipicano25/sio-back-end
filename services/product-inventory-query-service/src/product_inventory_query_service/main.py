"""Punto de entrada de product-inventory-query-service (spec 022).

Servicio de solo lectura y sin base de datos. Las rutas son privadas por defecto; solo la salud y,
si `SIO_DOCS_ENABLED`, la documentación son públicas, por ruta exacta (Principio V).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sio_auth import SIOAuth

from product_inventory_query_service.api.dependencies import Dependencies, PortsFactory, build_http_dependencies, build_runtime
from product_inventory_query_service.api.errors import register_error_handlers
from product_inventory_query_service.api.health import ReadinessProbe
from product_inventory_query_service.api.health import build_router as build_health_router
from product_inventory_query_service.api.openapi import OPENAPI_TAGS, configure_bearer_openapi
from product_inventory_query_service.api.routers import include_api_routers
from product_inventory_query_service.api.security import build_auth
from product_inventory_query_service.api.tracing import TracingMiddleware
from product_inventory_query_service.config import Settings, load_settings
from product_inventory_query_service.infrastructure.jwks_probe import build_jwks_probe
from product_inventory_query_service.observability import configure_logging

SERVICE_TITLE = "SIO Product Inventory Query Service"
SERVICE_VERSION = "0.1.0"
API_PREFIX = "/api/v1"

HEALTH_PUBLIC_PATHS = {"/health/live", "/health/ready"}
DOCS_PUBLIC_PATHS = {"/docs", "/openapi.json"}


def create_app(
    settings: Settings | None = None,
    *,
    auth: SIOAuth | None = None,
    jwks_probe: ReadinessProbe | None = None,
    ports_factory: PortsFactory | None = None,
) -> FastAPI:
    """Construye la aplicación FastAPI.

    Los parámetros solo los inyectan las pruebas; si se omiten se usan los adaptadores reales (HTTP hacia OC, CR,
    PC e Inventory y token técnico de Keycloak).
    """
    current_settings = settings or load_settings()
    configure_logging()

    if ports_factory is None:
        dependencies = build_http_dependencies(current_settings)
    else:
        async def nothing() -> None:
            return None

        dependencies = Dependencies(ports_factory, build_runtime(current_settings), nothing)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await dependencies.close()

    app = FastAPI(
        title=SERVICE_TITLE,
        description=(
            "Consultas de solo lectura de SIO: productos con presentaciones, precios, imágenes y existencias; "
            "inventario por sucursal y consolidado; productos bajo mínimo y resumen de inventario. Sin base de "
            "datos: compone por HTTP los datos de sus servicios propietarios."
        ),
        version=SERVICE_VERSION,
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs" if current_settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if current_settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = current_settings
    app.state.dependencies = dependencies

    public_paths = set(HEALTH_PUBLIC_PATHS)

    if current_settings.docs_enabled:
        public_paths.update(DOCS_PUBLIC_PATHS)
        configure_bearer_openapi(app=app, public_paths=public_paths)

    current_auth = auth or build_auth()

    register_error_handlers(app)
    app.include_router(build_health_router(jwks_probe or build_jwks_probe(current_settings)))
    include_api_routers(app, current_auth, prefix=API_PREFIX)

    current_auth.protect(app, public_paths=public_paths)
    # Último middleware agregado = más externo: envuelve también a sio-auth.
    app.add_middleware(TracingMiddleware)

    return app


def __getattr__(name: str):
    """`product_inventory_query_service.main:app` se construye al primer acceso (Uvicorn), no al importar."""
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
