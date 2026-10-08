"""Punto de entrada de Sales Service."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from sio_auth import SIOAuth

from sales_service.api.dependencies import AccessFactory, DirectoriesFactory, InventoryFactory
from sales_service.api.errors import register_error_handlers
from sales_service.api.health import build_router as build_health_router
from sales_service.api.openapi import OPENAPI_TAGS, configure_bearer_openapi
from sales_service.api.routers import include_api_routers
from sales_service.api.security import build_auth
from sales_service.api.tracing import TracingMiddleware
from sales_service.application.ports import Directories, TokenProvider
from sales_service.config import Settings, load_settings
from sales_service.infrastructure.commercial_relationship_directory import HTTPCommercialDirectory
from sales_service.infrastructure.database import Database
from sales_service.infrastructure.inventory_gateway import HTTPInventoryGateway
from sales_service.infrastructure.keycloak_token_client import KeycloakTokenClient
from sales_service.infrastructure.operational_context_directory import (
    HTTPAccessDirectory,
    HTTPOperationalContextDirectory,
)
from sales_service.infrastructure.party_identity_directory import HTTPPartyDirectory
from sales_service.infrastructure.product_catalog_directory import HTTPCatalogDirectory
from sales_service.observability import configure_logging

SERVICE_TITLE = "SIO Sales Service"
SERVICE_VERSION = "0.1.0"
API_PREFIX = "/api/v1"

HEALTH_PUBLIC_PATHS = {"/health/live", "/health/ready"}
DOCS_PUBLIC_PATHS = {"/docs", "/openapi.json"}


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_token_provider(settings: Settings) -> TokenProvider:
    return KeycloakTokenClient(
        token_url=settings.keycloak_token_url,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        timeout_seconds=settings.operational_context_timeout_seconds,
    )


def build_directories(settings: Settings, tokens: TokenProvider) -> DirectoriesFactory:
    def factory() -> Directories:
        return Directories(
            operational_context=HTTPOperationalContextDirectory(
                base_url=settings.operational_context_base_url,
                timeout_seconds=settings.operational_context_timeout_seconds,
                tokens=tokens,
            ),
            commercial=HTTPCommercialDirectory(
                base_url=settings.commercial_relationship_base_url,
                timeout_seconds=settings.commercial_relationship_timeout_seconds,
                tokens=tokens,
            ),
            catalog=HTTPCatalogDirectory(
                base_url=settings.product_catalog_base_url,
                timeout_seconds=settings.product_catalog_timeout_seconds,
                tokens=tokens,
            ),
            party=HTTPPartyDirectory(
                base_url=settings.party_identity_base_url,
                timeout_seconds=settings.party_identity_timeout_seconds,
                tokens=tokens,
            ),
        )

    return factory


def build_inventory(settings: Settings, tokens: TokenProvider) -> InventoryFactory:
    return lambda: HTTPInventoryGateway(
        base_url=settings.inventory_base_url, timeout_seconds=settings.inventory_timeout_seconds, tokens=tokens
    )


def create_app(
    settings: Settings | None = None,
    *,
    auth: SIOAuth | None = None,
    token_provider: TokenProvider | None = None,
    directories_factory: DirectoriesFactory | None = None,
    inventory_factory: InventoryFactory | None = None,
    access_factory: AccessFactory | None = None,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    """Construye la aplicación FastAPI.

    Las fábricas solo las inyectan las pruebas; si se omiten se usan siempre los adaptadores
    HTTP reales (sin modos por entorno).
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
            "Ventas de SIO: borrador con validación de cliente, productos, presentaciones y precio resuelto; "
            "consulta de existencias; confirmación idempotente que descuenta Inventory, guarda el costo FIFO y el "
            "margen y asigna el número del período; anulación con reverso exacto; secuencias de numeración."
        ),
        version=SERVICE_VERSION,
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs" if current_settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if current_settings.docs_enabled else None,
        lifespan=lifespan,
    )

    def default_access(request: Request) -> HTTPAccessDirectory:
        return HTTPAccessDirectory(
            base_url=current_settings.operational_context_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=current_settings.operational_context_timeout_seconds,
        )

    app.state.settings = current_settings
    app.state.database = database
    app.state.clock = clock or utc_now
    app.state.directories_factory = directories_factory or build_directories(current_settings, tokens)
    app.state.inventory_factory = inventory_factory or build_inventory(current_settings, tokens)
    app.state.access_factory = access_factory or default_access

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
    """`sales_service.main:app` se construye al primer acceso (Uvicorn), no al importar."""
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
