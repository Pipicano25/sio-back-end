"""Construcción de los puertos de cada solicitud (Principio XV; spec 023, DR-07).

Todas las dependencias se consumen **con el token del usuario** de la solicitud: los adaptadores se crean por
solicitud sobre un cliente HTTP compartido por proveedor. Sin cliente técnico ni token propio. Las pruebas
inyectan en `create_app` una fábrica de puertos con dobles.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request

from business_reporting_service.application.exceptions import (
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    OPERATIONAL_CONTEXT,
    PRODUCT_CATALOG,
    PURCHASE,
    SALES,
)
from business_reporting_service.application.ports import Ports
from business_reporting_service.config import Settings
from business_reporting_service.infrastructure.catalog import HTTPCommercialRelationship, HTTPProductCatalog
from business_reporting_service.infrastructure.http_client import AsyncDependencyClient, UserCaller
from business_reporting_service.infrastructure.inventory import HTTPInventory
from business_reporting_service.infrastructure.operational_context import HTTPOperationalContext
from business_reporting_service.infrastructure.purchase import HTTPPurchase
from business_reporting_service.infrastructure.sales import HTTPSales

PortsFactory = Callable[[str | None], Ports]
"""Recibe la cabecera `Authorization` del usuario y devuelve los puertos de la solicitud."""


@dataclass(frozen=True, slots=True)
class Dependencies:
    ports_factory: PortsFactory
    close: Callable[[], Awaitable[None]]


def build_http_dependencies(settings: Settings) -> Dependencies:
    timeout = settings.dependency_timeout_seconds
    clients = {
        OPERATIONAL_CONTEXT: AsyncDependencyClient(provider=OPERATIONAL_CONTEXT,
                                                   base_url=settings.operational_context_base_url, timeout_seconds=timeout),
        SALES: AsyncDependencyClient(provider=SALES, base_url=settings.sales_base_url, timeout_seconds=timeout),
        PURCHASE: AsyncDependencyClient(provider=PURCHASE, base_url=settings.purchase_base_url, timeout_seconds=timeout),
        INVENTORY: AsyncDependencyClient(provider=INVENTORY, base_url=settings.inventory_base_url, timeout_seconds=timeout),
        COMMERCIAL_RELATIONSHIP: AsyncDependencyClient(provider=COMMERCIAL_RELATIONSHIP,
                                                       base_url=settings.commercial_relationship_base_url,
                                                       timeout_seconds=timeout),
        PRODUCT_CATALOG: AsyncDependencyClient(provider=PRODUCT_CATALOG, base_url=settings.product_catalog_base_url,
                                               timeout_seconds=timeout),
    }

    def factory(authorization: str | None) -> Ports:
        def user(name: str) -> UserCaller:
            return UserCaller(clients[name], authorization)

        return Ports(
            oc=HTTPOperationalContext(clients[OPERATIONAL_CONTEXT], authorization),
            sales=HTTPSales(user(SALES)),
            purchase=HTTPPurchase(user(PURCHASE)),
            inventory=HTTPInventory(user(INVENTORY)),
            cr=HTTPCommercialRelationship(user(COMMERCIAL_RELATIONSHIP)),
            pc=HTTPProductCatalog(user(PRODUCT_CATALOG)),
        )

    async def close() -> None:
        for client in clients.values():
            await client.aclose()

    return Dependencies(factory, close)


def ports_of(request: Request) -> Ports:
    dependencies: Dependencies = request.app.state.dependencies
    return dependencies.ports_factory(request.headers.get("authorization"))
