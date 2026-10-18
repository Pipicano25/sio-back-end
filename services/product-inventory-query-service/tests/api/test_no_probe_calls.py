"""Sin sondeos, sin llamadas repetidas y sin dependencia del tamaño de la empresa (T124; CP-90, CP-101, CP-102;
SC-022-8; FR-022-130, FR-022-138).
"""

from __future__ import annotations

from collections import Counter
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from product_inventory_query_service.application.listing import Ports
from product_inventory_query_service.main import create_app
from tests.api.support import World
from tests.conftest import build_test_settings
from tests.fakes import build_fakes

COUNTS = {"count_adopted", "summary"}
"""Las únicas operaciones de conteo o agregado: solo las usa el resumen."""

QUERIES = {
    "R-E": ("product-overviews", ""),
    "R-B": ("product-overviews", "search=prod&has_image=true&stock_state=IN_STOCK"),
    "R-A2": ("product-overviews", "internal_code=C00003"),
    "R-A1": ("product-overviews", "barcode=7700000003"),
    "R-C": ("inventory-overviews", "brand_id={brand}&stock_state=OUT_OF_STOCK"),
    "R-D": ("inventory-overviews", "stock_state=IN_STOCK&minimum_state=NO_POLICY"),
    "R-F": ("product-overviews", "brand_id={brand}&sort=created_at:desc"),
    "R-D pares": ("low-stock-products", "brand_id={brand}"),
    "R-F pares": ("low-stock-products", "sort=display_name"),
}


def populate(world: World, count: int, brand) -> None:
    for index in range(count):
        item = world.product(f"Producto {index:05d}", brand=brand if index % 3 == 0 else None, has_image=index % 2 == 0,
                             identifiers={f"77{index:08d}"}, internal_code=f"C{index:05d}")
        if index % 4 == 0:
            world.stock(item, str(index % 7), branch=index % 2)
        if index % 5 == 0:
            world.minimum(item, "3", branch=0)


@pytest.mark.parametrize("route", list(QUERIES))
def test_listings_never_count_or_probe_and_never_repeat_a_call(world, as_user, route) -> None:
    """CP-90 y CP-101: los dobles fallan ante un conteo; ninguna operación se repite con los mismos argumentos."""
    brand = uuid4()
    populate(world, 300, brand)
    world.fakes.cr.forbidden |= {"count_adopted"}
    world.fakes.inventory.forbidden |= {"summary"}
    endpoint, query = QUERIES[route]
    response = as_user("supervisor.test").get(f"{world.base}/{endpoint}?{query.format(brand=brand)}")
    assert response.status_code == 200, response.text
    assert world.fakes.log.repeated() == []
    assert not any(world.fakes.log.count(name) for name in COUNTS)


@pytest.mark.parametrize("route", ["R-E", "R-B", "R-C", "R-D pares"])
def test_the_same_page_makes_the_same_calls_with_2000_and_20000_products(test_auth, user_token, route) -> None:
    """CP-102: el número y el tipo de llamadas no dependen del número de productos de la empresa."""
    endpoint, query = QUERIES[route]
    results = []
    for count in (2000, 20000):
        fakes = build_fakes()
        world = World.create(fakes)
        brand = uuid4()
        populate(world, count, brand)
        app = create_app(build_test_settings(), auth=test_auth, jwks_probe=lambda: True,
                         ports_factory=lambda authorization, f=fakes: Ports(f.oc, f.cr, f.pc, f.inventory))
        with TestClient(app) as client:
            response = client.get(f"{world.base}/{endpoint}?{query.format(brand=brand)}",
                                  headers={"Authorization": f"Bearer {user_token('supervisor.test')}"})
        assert response.status_code == 200, response.text
        results.append(Counter(fakes.log.order))
    assert results[0] == results[1]
    # Tanda 0 (2) + como máximo 5 lotes (conductor, CR, PC y 2 por sucursal) + enriquecimiento (≤ 12).
    assert sum(results[0].values()) <= 2 + 5 * (1 + 1 + 1 + 2 * 2) + 12
