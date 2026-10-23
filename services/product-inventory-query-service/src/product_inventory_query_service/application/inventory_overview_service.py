"""Caso de uso de `inventory-overviews` (FR-022-40 a FR-022-43; T109).

Reutiliza el planificador, la búsqueda progresiva y el enriquecimiento de `product-overviews`. El conjunto base son
los productos con control de inventario (CR lo aplica como conductor o evaluador, `product_criteria`). Los precios
nunca se piden: el esquema no los tiene.
"""

from __future__ import annotations

from product_inventory_query_service.application.enrichment import ProductView, enrich_products
from product_inventory_query_service.application.listing import Listing, ListingResult, Ports, Runtime, run_listing
from product_inventory_query_service.application.product_overview_service import Visibility
from product_inventory_query_service.domain.pagination import Page
from product_inventory_query_service.domain.query_spec import QuerySpec


async def inventory_overviews(spec: QuerySpec, visibility: Visibility, ports: Ports, runtime: Runtime
                              ) -> tuple[ListingResult, list[ProductView]]:
    async def enrich(listing: Listing, page: Page) -> list[ProductView]:
        return await enrich_products(
            listing.gateway, [listing.product_of(item) for item in page.items], listing.branch_ids,
            with_prices=False, price_list_id=None, with_stock=visibility.stock,
            with_minimums=visibility.stock and visibility.minimums, include_images=spec.include_images,
        )

    return await run_listing(spec, ports, runtime, enrich=enrich)
