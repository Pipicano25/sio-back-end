"""Construcción de los puertos y de la configuración de ejecución (Principio XV; research R-01 a R-03).

- Operational Context se consume **con el token del usuario** de cada solicitud (D5): su adaptador se crea por
  solicitud sobre un cliente HTTP compartido.
- CR, PC e Inventory se consumen con la identidad técnica (`client_credentials`), un cliente HTTP por proveedor y
  un único token en memoria.

Las pruebas inyectan en `create_app` una fábrica de puertos con dobles.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request

from product_inventory_query_service.application.exceptions import (
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    OPERATIONAL_CONTEXT,
    PRODUCT_CATALOG,
)
from product_inventory_query_service.application.listing import Ports, Runtime
from product_inventory_query_service.config import Settings
from product_inventory_query_service.domain.cursor import CursorCodec
from product_inventory_query_service.domain.planner import BatchPolicy
from product_inventory_query_service.infrastructure.commercial_relationship import HTTPCommercialRelationship
from product_inventory_query_service.infrastructure.http_client import AsyncDependencyClient, TechnicalCaller
from product_inventory_query_service.infrastructure.inventory import HTTPInventory
from product_inventory_query_service.infrastructure.keycloak_token_client import KeycloakTokenClient
from product_inventory_query_service.infrastructure.operational_context import HTTPOperationalContext
from product_inventory_query_service.infrastructure.product_catalog import HTTPProductCatalog

PortsFactory = Callable[[str | None], Ports]
"""Recibe la cabecera `Authorization` del usuario y devuelve los puertos de la solicitud."""


@dataclass(frozen=True, slots=True)
class Dependencies:
    ports_factory: PortsFactory
    runtime: Runtime
    close: Callable[[], Awaitable[None]]


def build_runtime(settings: Settings) -> Runtime:
    return Runtime(
        codec=CursorCodec(settings.cursor_secret, settings.cursor_secret_previous, ttl_seconds=settings.cursor_ttl_seconds),
        policy=BatchPolicy(
            minimum=settings.batch_min,
            factor=settings.batch_factor,
            maximum=settings.batch_max,
            max_batches=settings.max_batches_per_request,
            work_time_seconds=settings.work_time_seconds,
        ),
        request_budget_seconds=settings.request_budget_seconds,
        max_parallel_calls=settings.max_parallel_calls,
    )


def build_http_dependencies(settings: Settings) -> Dependencies:
    timeout = settings.dependency_timeout_seconds

    def client(provider: str, base_url: str) -> AsyncDependencyClient:
        return AsyncDependencyClient(provider=provider, base_url=base_url, timeout_seconds=timeout)

    oc_client = client(OPERATIONAL_CONTEXT, settings.operational_context_base_url)
    cr_client = client(COMMERCIAL_RELATIONSHIP, settings.commercial_relationship_base_url)
    pc_client = client(PRODUCT_CATALOG, settings.product_catalog_base_url)
    inventory_client = client(INVENTORY, settings.inventory_base_url)
    tokens = KeycloakTokenClient(
        token_url=settings.keycloak_token_url,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        timeout_seconds=timeout,
    )
    cr = HTTPCommercialRelationship(TechnicalCaller(cr_client, tokens))
    pc = HTTPProductCatalog(TechnicalCaller(pc_client, tokens))
    inventory = HTTPInventory(TechnicalCaller(inventory_client, tokens))

    def factory(authorization: str | None) -> Ports:
        return Ports(HTTPOperationalContext(oc_client, authorization), cr, pc, inventory)

    async def close() -> None:
        for item in (oc_client, cr_client, pc_client, inventory_client):
            await item.aclose()

    return Dependencies(factory, build_runtime(settings), close)


def ports_of(request: Request) -> Ports:
    dependencies: Dependencies = request.app.state.dependencies
    return dependencies.ports_factory(request.headers.get("authorization"))


def runtime_of(request: Request) -> Runtime:
    return request.app.state.dependencies.runtime
