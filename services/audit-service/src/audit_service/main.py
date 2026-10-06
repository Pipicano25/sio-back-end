"""Punto de entrada de Audit Service."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sio_auth import SIOAuth

from audit_service.api.audit_events import build_router as build_registration_router
from audit_service.api.company_audit_events import build_company_router
from audit_service.api.dependencies import AccessDirectoryFactory
from audit_service.api.errors import register_error_handlers
from audit_service.api.health import build_router as build_health_router
from audit_service.api.openapi import OPENAPI_TAGS, configure_bearer_openapi
from audit_service.api.platform_audit_events import build_platform_router
from audit_service.api.security import build_auth
from audit_service.api.tracing import TracingMiddleware
from audit_service.config import Settings, load_settings
from audit_service.infrastructure.database import Database
from audit_service.infrastructure.operational_context_directory import HTTPCompanyAccessDirectory
from audit_service.observability import configure_logging

SERVICE_TITLE = "SIO Audit Service"
SERVICE_VERSION = "0.1.0"
API_PREFIX = "/api/v1"

HEALTH_PUBLIC_PATHS = {"/health/live", "/health/ready"}
DOCS_PUBLIC_PATHS = {"/docs", "/openapi.json"}


def build_access_directory_factory(settings: Settings) -> AccessDirectoryFactory:
    """Operational Context `operational-access` con el token del usuario (FR-050)."""

    def factory(request: Request) -> HTTPCompanyAccessDirectory:
        return HTTPCompanyAccessDirectory(
            base_url=settings.operational_context_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=settings.operational_context_timeout_seconds,
        )

    return factory


def create_app(
    settings: Settings | None = None,
    *,
    auth: SIOAuth | None = None,
    access_directory_factory: AccessDirectoryFactory | None = None,
) -> FastAPI:
    """Construye la aplicación FastAPI.

    La fábrica de Operational Context solo la inyectan las pruebas; si se omite
    se usa siempre el adaptador HTTP real (sin modos por entorno).
    """
    current_settings = settings or load_settings()
    configure_logging()
    database = Database(current_settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        database.dispose()

    app = FastAPI(
        title=SERVICE_TITLE,
        description=(
            "Registro oficial e inmutable de las acciones importantes de SIO: los "
            "microservicios registran eventos con su identidad técnica y los usuarios "
            "autorizados los consultan por empresa o, con un permiso propio, los de plataforma."
        ),
        version=SERVICE_VERSION,
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs" if current_settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if current_settings.docs_enabled else None,
        lifespan=lifespan,
    )

    app.state.settings = current_settings
    app.state.database = database
    app.state.access_directory_factory = access_directory_factory or build_access_directory_factory(
        current_settings
    )

    public_paths = set(HEALTH_PUBLIC_PATHS)

    if current_settings.docs_enabled:
        public_paths.update(DOCS_PUBLIC_PATHS)
        configure_bearer_openapi(app=app, public_paths=public_paths)

    current_auth = auth or build_auth()

    register_error_handlers(app)
    app.include_router(build_health_router(database))
    app.include_router(build_registration_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_company_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_platform_router(current_auth), prefix=API_PREFIX)

    current_auth.protect(app, public_paths=public_paths)
    # Último middleware agregado = más externo: envuelve también a sio-auth.
    app.add_middleware(TracingMiddleware)

    return app


def __getattr__(name: str):
    """`audit_service.main:app` se construye al primer acceso (Uvicorn), no al importar."""
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
