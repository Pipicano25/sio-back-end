"""Punto de entrada de business-reporting-service (spec 023).

Servicio de solo lectura, sin base de datos, colas ni tareas programadas: cada reporte se calcula cuando un
usuario lo pide. Las rutas son privadas por defecto; solo la salud y, si `SIO_DOCS_ENABLED`, la documentación son
públicas, por ruta exacta (Principio V).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from sio_auth import SIOAuth

from business_reporting_service.api.dependencies import Dependencies, PortsFactory, build_http_dependencies
from business_reporting_service.api.errors import register_error_handlers
from business_reporting_service.api.health import ReadinessProbe
from business_reporting_service.api.health import build_router as build_health_router
from business_reporting_service.api.openapi import OPENAPI_TAGS, configure_bearer_openapi
from business_reporting_service.api.routers import include_api_routers
from business_reporting_service.api.security import build_auth
from business_reporting_service.api.tracing import TracingMiddleware
from business_reporting_service.config import Settings, load_settings
from business_reporting_service.infrastructure.jwks_probe import build_jwks_probe
from business_reporting_service.observability import configure_logging

SERVICE_TITLE = "SIO Business Reporting Service"
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
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    """Construye la aplicación FastAPI.

    Los parámetros solo los inyectan las pruebas; si se omiten se usan los adaptadores reales (HTTP hacia OC,
    Sales, Purchase, Inventory, CR y PC con el token del usuario).
    """
    current_settings = settings or load_settings()
    configure_logging()

    if ports_factory is None:
        dependencies = build_http_dependencies(current_settings)
    else:
        async def nothing() -> None:
            return None

        dependencies = Dependencies(ports_factory, nothing)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await dependencies.close()

    app = FastAPI(
        title=SERVICE_TITLE,
        description=(
            "Reportes empresariales y operativos de solo lectura de SIO, bajo demanda en JSON y CSV: productos más "
            "vendidos, ventas por sucursal, compras del período y evolución de existencias. Sin base de datos: "
            "consume las agregaciones de Sales, Purchase e Inventory con el token del usuario."
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
    app.state.clock = clock or (lambda: datetime.now(UTC))

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
    """`business_reporting_service.main:app` se construye al primer acceso (Uvicorn), no al importar."""
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
