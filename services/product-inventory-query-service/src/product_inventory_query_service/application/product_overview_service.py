"""Caso de uso de `product-overviews` (FR-022-30 a FR-022-35; T105).

Autorización previa, plan, cursor, búsqueda progresiva y página (`run_listing`), y después el enriquecimiento de
los productos de la página con los bloques visibles. Los bloques los decide la capa API con los permisos del
token (FR-022-14); este caso de uso solo recibe qué puede pedir.
"""

from __future__ import annotations

from dataclasses import dataclass

from product_inventory_query_service.application.enrichment import ProductView, enrich_products
from product_inventory_query_service.application.listing import Listing, ListingResult, Ports, Runtime, run_listing
from product_inventory_query_service.domain.pagination import Page
from product_inventory_query_service.domain.query_spec import QuerySpec


@dataclass(frozen=True, slots=True)
class Visibility:
    prices: bool = False
    stock: bool = False
    minimums: bool = False


async def product_overviews(spec: QuerySpec, visibility: Visibility, ports: Ports, runtime: Runtime
                            ) -> tuple[ListingResult, list[ProductView]]:
    async def enrich(listing: Listing, page: Page) -> list[ProductView]:
        return await enrich_products(
            listing.gateway, [listing.product_of(item) for item in page.items], listing.branch_ids,
            with_prices=visibility.prices, price_list_id=spec.price_list_id, with_stock=visibility.stock,
            with_minimums=visibility.stock and visibility.minimums,
        )

    return await run_listing(spec, ports, runtime, enrich=enrich)
