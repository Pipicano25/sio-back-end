"""Punto de entrada de Purchase Service."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, fields
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from sio_auth import SIOAuth, install_cors
from sio_contract_read import ContractReadSettings, create_contract_engine
from sqlalchemy import Engine

from purchase_service.api.dependencies import AccessFactory, DirectoriesFactory, InventoryFactory
from purchase_service.api.errors import register_error_handlers
from purchase_service.api.health import build_router as build_health_router
from purchase_service.api.openapi import OPENAPI_TAGS, configure_bearer_openapi
from purchase_service.api.routers import include_api_routers
from purchase_service.api.security import build_auth
from purchase_service.api.tracing import TracingMiddleware
from purchase_service.application.ports import Directories, TokenProvider
from purchase_service.config import Settings, load_settings
from purchase_service.infrastructure.commercial_relationship_directory import HTTPCommercialDirectory
from purchase_service.infrastructure.contract_commercial_relationship import ContractCommercialDirectory
from purchase_service.infrastructure.contract_inventory import ContractInventoryGateway
from purchase_service.infrastructure.contract_operational_context import (
    ContractAccessDirectory,
    ContractOperationalContextDirectory,
)
from purchase_service.infrastructure.contract_party_identity import ContractPartyDirectory
from purchase_service.infrastructure.contract_payment_reference import ContractPaymentReferenceDirectory
from purchase_service.infrastructure.contract_product_catalog import ContractCatalogDirectory
from purchase_service.infrastructure.database import Database
from purchase_service.infrastructure.inventory_gateway import HTTPInventoryGateway
from purchase_service.infrastructure.keycloak_token_client import KeycloakTokenClient
from purchase_service.infrastructure.operational_context_directory import (
    HTTPAccessDirectory,
    HTTPOperationalContextDirectory,
)
from purchase_service.infrastructure.party_identity_directory import HTTPPartyDirectory
from purchase_service.infrastructure.payment_reference_directory import HTTPPaymentReferenceDirectory
from purchase_service.infrastructure.product_catalog_directory import HTTPCatalogDirectory
from purchase_service.observability import configure_logging

SERVICE_TITLE = "SIO Purchase Service"
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


@dataclass(frozen=True, slots=True)
class ContractEngines:
    """Motores de lectura por vistas de contrato (spec 025, D27); `None` = ese propietario se lee por HTTP."""

    operational_context: Engine | None = None
    product_catalog: Engine | None = None
    commercial_relationship: Engine | None = None
    party_identity: Engine | None = None
    payment_reference: Engine | None = None
    inventory: Engine | None = None

    def dispose(self) -> None:
        for item in fields(self):
            engine = getattr(self, item.name)
            if engine is not None:
                engine.dispose()


def _engine(reads: ContractReadSettings | None) -> Engine | None:
    if reads is None or not reads.uses_contract:
        return None
    return create_contract_engine(reads, application_name="purchase-service")


def build_contract_engines(settings: Settings) -> ContractEngines:
    """Un motor por propietario con `<PROPIETARIO>_READ_SOURCE=contract`."""
    return ContractEngines(
        operational_context=_engine(settings.operational_context_reads),
        product_catalog=_engine(settings.product_catalog_reads),
        commercial_relationship=_engine(settings.commercial_relationship_reads),
        party_identity=_engine(settings.party_identity_reads),
        payment_reference=_engine(settings.payment_reference_reads),
        inventory=_engine(settings.inventory_reads),
    )


def build_directories(
    settings: Settings, tokens: TokenProvider, engines: ContractEngines | None = None
) -> DirectoriesFactory:
    current = engines or ContractEngines()

    def factory() -> Directories:
        return Directories(
            operational_context=(
                ContractOperationalContextDirectory(engine=current.operational_context)
                if current.operational_context is not None
                else HTTPOperationalContextDirectory(
                    base_url=settings.operational_context_base_url,
                    timeout_seconds=settings.operational_context_timeout_seconds,
                    tokens=tokens,
                )
            ),
            commercial=(
                ContractCommercialDirectory(engine=current.commercial_relationship)
                if current.commercial_relationship is not None
                else HTTPCommercialDirectory(
                    base_url=settings.commercial_relationship_base_url,
                    timeout_seconds=settings.commercial_relationship_timeout_seconds,
                    tokens=tokens,
                )
            ),
            catalog=(
                ContractCatalogDirectory(engine=current.product_catalog)
                if current.product_catalog is not None
                else HTTPCatalogDirectory(
                    base_url=settings.product_catalog_base_url,
                    timeout_seconds=settings.product_catalog_timeout_seconds,
                    tokens=tokens,
                )
            ),
            party=(
                ContractPartyDirectory(engine=current.party_identity)
                if current.party_identity is not None
                else HTTPPartyDirectory(
                    base_url=settings.party_identity_base_url,
                    timeout_seconds=settings.party_identity_timeout_seconds,
                    tokens=tokens,
                )
            ),
            payment_reference=(
                ContractPaymentReferenceDirectory(engine=current.payment_reference)
                if current.payment_reference is not None
                else HTTPPaymentReferenceDirectory(
                    base_url=settings.payment_reference_base_url,
                    timeout_seconds=settings.payment_reference_timeout_seconds,
                    tokens=tokens,
                )
            ),
        )

    return factory


def build_inventory(
    settings: Settings, tokens: TokenProvider, engines: ContractEngines | None = None
) -> InventoryFactory:
    current = engines or ContractEngines()

    def factory() -> HTTPInventoryGateway | ContractInventoryGateway:
        http = HTTPInventoryGateway(
            base_url=settings.inventory_base_url, timeout_seconds=settings.inventory_timeout_seconds, tokens=tokens
        )
        if current.inventory is None:
            return http
        return ContractInventoryGateway(engine=current.inventory, http=http)

    return factory


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

    # Spec 025 (D27): cada propietario con `<PROPIETARIO>_READ_SOURCE=contract` se lee de sus vistas de contrato.
    engines = build_contract_engines(current_settings)
    oc_contract = engines.operational_context

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        database.dispose()
        engines.dispose()

    app = FastAPI(
        title=SERVICE_TITLE,
        description=(
            "Compras de SIO: borrador con validación de proveedor, productos y presentaciones; confirmación "
            "idempotente que ingresa la mercancía en Inventory y asigna el número del período; anulación con "
            "reverso exacto; hitos logísticos; secuencias de numeración."
        ),
        version=SERVICE_VERSION,
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs" if current_settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if current_settings.docs_enabled else None,
        lifespan=lifespan,
    )

    def default_access(request: Request) -> HTTPAccessDirectory | ContractAccessDirectory:
        if oc_contract is not None:
            return ContractAccessDirectory(engine=oc_contract, claims=getattr(request.state, "sio_claims", None))
        return HTTPAccessDirectory(
            base_url=current_settings.operational_context_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=current_settings.operational_context_timeout_seconds,
        )

    app.state.settings = current_settings
    app.state.database = database
    app.state.clock = clock or utc_now
    app.state.directories_factory = directories_factory or build_directories(current_settings, tokens, engines)
    app.state.inventory_factory = inventory_factory or build_inventory(current_settings, tokens, engines)
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
    # CORS abierto envuelve toda la pila, incluido el manejo de errores (sio-auth 0.5.0).
    install_cors(app)

    return app


def __getattr__(name: str):
    """`purchase_service.main:app` se construye al primer acceso (Uvicorn), no al importar."""
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)
