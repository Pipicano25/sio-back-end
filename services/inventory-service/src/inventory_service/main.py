"""Punto de entrada de Inventory Service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, Request
from sio_auth import SIOAuth

from inventory_service.api.dependencies import (
    AccessDirectoryFactory,
    CompanyProductFactory,
    OperationalContextFactory,
)
from inventory_service.api.errors import register_error_handlers
from inventory_service.api.health import build_router as build_health_router
from inventory_service.api.openapi import OPENAPI_TAGS, configure_bearer_openapi
from inventory_service.api.routers import include_api_routers
from inventory_service.api.security import build_auth
from inventory_service.api.tracing import TracingMiddleware
from inventory_service.application.audit_events import make_audit_hook
from inventory_service.application.ports import TokenProvider
from inventory_service.config import Settings, load_settings
from inventory_service.infrastructure.commercial_relationship_directory import HTTPCompanyProductDirectory
from inventory_service.infrastructure.database import Database
from inventory_service.infrastructure.keycloak_token_client import KeycloakTokenClient
from inventory_service.infrastructure.operational_context_directory import (
    HTTPCompanyAccessDirectory,
    HTTPOperationalContextDirectory,
)
from inventory_service.observability import configure_logging, current_trace_id

SERVICE_TITLE = "SIO Inventory Service"
SERVICE_VERSION = "0.1.0"
API_PREFIX = "/api/v1"

HEALTH_PUBLIC_PATHS = {"/health/live", "/health/ready"}
DOCS_PUBLIC_PATHS = {"/docs", "/openapi.json"}


def build_token_provider(settings: Settings) -> TokenProvider:
    return KeycloakTokenClient(
        token_url=settings.keycloak_token_url,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        timeout_seconds=max(settings.operational_context_timeout_seconds, settings.commercial_relationship_timeout_seconds),
    )


def _request_id() -> UUID | None:
    """`request_id` del evento de auditoría = `trace_id` de la solicitud (R-11)."""
    trace_id = current_trace_id()
    return UUID(hex=trace_id) if trace_id else None


def create_app(
    settings: Settings | None = None,
    *,
    auth: SIOAuth | None = None,
    token_provider: TokenProvider | None = None,
    operational_context_factory: OperationalContextFactory | None = None,
    commercial_relationship_factory: CompanyProductFactory | None = None,
    access_directory_factory: AccessDirectoryFactory | None = None,
) -> FastAPI:
    """Construye la aplicación FastAPI.

    Las fábricas de dependencias solo las inyectan las pruebas; si se omiten se usan
    siempre los adaptadores HTTP reales (sin modos por entorno).
    """
    current_settings = settings or load_settings()
    configure_logging()
    database = Database(current_settings.database_url, lock_timeout_seconds=current_settings.lock_timeout_seconds)
    tokens = token_provider or build_token_provider(current_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        database.dispose()

    app = FastAPI(
        title=SERVICE_TITLE,
        description=(
            "Motor central de inventario de SIO: saldos por empresa, sucursal y producto, "
            "kardex inmutable, entradas de compra, salidas de venta y sus reversos, aplicados "
            "solo por cuentas de servicio; consulta de stock y kardex aislada por empresa."
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
    app.state.operational_context_factory = operational_context_factory or (
        lambda: HTTPOperationalContextDirectory(
            base_url=current_settings.operational_context_base_url,
            timeout_seconds=current_settings.operational_context_timeout_seconds,
            tokens=tokens,
        )
    )
    app.state.commercial_relationship_factory = commercial_relationship_factory or (
        lambda: HTTPCompanyProductDirectory(
            base_url=current_settings.commercial_relationship_base_url,
            timeout_seconds=current_settings.commercial_relationship_timeout_seconds,
            tokens=tokens,
        )
    )

    def default_access(request: Request) -> HTTPCompanyAccessDirectory:
        return HTTPCompanyAccessDirectory(
            base_url=current_settings.operational_context_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=current_settings.operational_context_timeout_seconds,
        )

    app.state.access_directory_factory = access_directory_factory or default_access
    app.state.audit_hook = make_audit_hook(_request_id)
    app.state.request_id = _request_id

    public_paths = set(HEALTH_PUBLIC_PATHS)

    if current_settings.docs_enabled:
        public_paths.update(DOCS_PUBLIC_PATHS)
        configure_bearer_openapi(app=app, public_paths=public_paths)

    current_auth = auth or build_auth()

    register_error_handlers(app)
    app.include_router(build_health_router(database))
    include_api_routers(app, current_auth, prefix=API_PREFIX)

    current_auth.protect(app, public_paths=public_paths)
    # Último middleware agregado = más externo: envuelve también a sio-auth.
    app.add_middleware(TracingMiddleware)

    return app


def __getattr__(name: str):
    """`inventory_service.main:app` se construye al primer acceso (Uvicorn), no al importar."""
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
