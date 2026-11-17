"""Punto de entrada de Product Catalog Service."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from sio_auth import SIOAuth, install_cors
from sio_contract_read import create_contract_engine

import product_catalog_service.application.audit_events  # noqa: F401  (registra la outbox de auditoría, feature 016)
from product_catalog_service.audit_context import bind_audit_actor
from product_catalog_service.api.errors import register_error_handlers
from product_catalog_service.api.health import build_router as build_health_router
from product_catalog_service.api.openapi import configure_bearer_openapi
from product_catalog_service.api.public_images import PUBLIC_IMAGE_PATH
from product_catalog_service.api.public_images import build_router as build_public_images_router
from product_catalog_service.api.routers import include_domain_routers
from product_catalog_service.api.security import build_auth
from product_catalog_service.api.tracing import TracingMiddleware, configure_logging
from product_catalog_service.application.ports import ManufacturerDirectory
from product_catalog_service.application.ports import AssetStorage
from product_catalog_service.config import Settings, load_settings
from product_catalog_service.infrastructure.s3_asset_storage import S3AssetStorage
from product_catalog_service.infrastructure.database import Database
from product_catalog_service.infrastructure.contract_party_identity import build_contract_manufacturer_directory
from product_catalog_service.infrastructure.party_identity_manufacturer_directory import (
    build_manufacturer_directory,
)

SERVICE_TITLE = "SIO Product Catalog Service"
SERVICE_VERSION = "0.1.0"

HEALTH_PUBLIC_PATHS = {
    "/health/live",
    "/health/ready",
}

DOCS_PUBLIC_PATHS = {
    "/docs",
    "/openapi.json",
}

ManufacturerDirectoryFactory = Callable[[Request], ManufacturerDirectory]


def build_manufacturer_directory_factory(settings: Settings, contract_engine=None) -> ManufacturerDirectoryFactory:
    """Party Identity con el token del usuario; con `contract_engine` (spec 025,
    `PARTY_IDENTITY_READ_SOURCE=contract`), la vista `v1_organization_identities` con el mismo permiso (FR-037)."""
    if contract_engine is not None:
        return lambda request: build_contract_manufacturer_directory(request, contract_engine)
    return lambda request: build_manufacturer_directory(request, settings)


def create_app(
    settings: Settings | None = None,
    *,
    auth: SIOAuth | None = None,
    manufacturer_directory_factory: ManufacturerDirectoryFactory | None = None,
    asset_storage: AssetStorage | None = None,
) -> FastAPI:
    """Construye la aplicación FastAPI del microservicio.

    Args:
        settings: Configuración opcional; por defecto se lee del entorno.
        auth: Fachada `sio-auth` opcional (las pruebas inyectan una con JWKS local).
        manufacturer_directory_factory: Fábrica opcional del adaptador de Party
            Identity por solicitud (las pruebas inyectan un doble).
        asset_storage: Almacenamiento de objetos del contenido de los activos; por
            defecto, el adaptador S3 configurado por `ASSET_STORAGE_*` (o ninguno).
    """
    current_settings = settings or load_settings()
    configure_logging()
    database = Database(current_settings.database_url)
    # Spec 025 (D27): con PARTY_IDENTITY_READ_SOURCE=contract el fabricante se lee de la vista de contrato.
    party_reads = current_settings.party_identity_reads
    party_engine = (
        create_contract_engine(party_reads, application_name="product-catalog-service")
        if party_reads is not None and party_reads.uses_contract and manufacturer_directory_factory is None
        else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        database.dispose()
        if party_engine is not None:
            party_engine.dispose()

    app = FastAPI(
        title=SERVICE_TITLE,
        description="Microservicio del catálogo global y compartido de productos de SIO.",
        version=SERVICE_VERSION,
        # Autor de auditoría de la solicitud (feature 016): no agrega parámetros a ninguna ruta.
        dependencies=[Depends(bind_audit_actor)],
        docs_url="/docs" if current_settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if current_settings.docs_enabled else None,
        lifespan=lifespan,
    )

    app.state.settings = current_settings
    app.state.database = database
    app.state.asset_storage = asset_storage if asset_storage is not None else S3AssetStorage.from_settings(current_settings)
    app.state.manufacturer_directory_factory = manufacturer_directory_factory or build_manufacturer_directory_factory(
        current_settings, party_engine
    )

    public_paths = set(HEALTH_PUBLIC_PATHS)

    if current_settings.docs_enabled:
        public_paths.update(DOCS_PUBLIC_PATHS)
        configure_bearer_openapi(app=app, public_paths=public_paths)

    current_auth = auth or build_auth()

    register_error_handlers(app)
    app.include_router(build_health_router(database))
    # Spec 022 (FR-022-90, FR-022-99): ruta pública exacta de imágenes, solo con secreto y URL pública base.
    if current_settings.public_images_enabled:
        app.include_router(build_public_images_router())
        public_paths.add(PUBLIC_IMAGE_PATH)
    include_domain_routers(app, current_auth)

    current_auth.protect(app, public_paths=public_paths)
    # Último middleware agregado = más externo: envuelve también a sio-auth.
    app.add_middleware(TracingMiddleware)
    # CORS abierto envuelve toda la pila, incluido el manejo de errores (sio-auth 0.5.0).
    install_cors(app)

    return app


app = create_app()
