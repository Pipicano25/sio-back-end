"""Imágenes en `product-overviews` (T101; FR-022-45 a FR-022-48; CP-10 a CP-20).

`has_image` e `image_url` llegan de PC-1 tal como los calcula Product Catalog (imagen principal `ACTIVE` y apta
para URL: CP-15 a CP-18 se prueban en PC). Este servicio los copia sin transformarlos y aplica el filtro
`has_image` sobre los candidatos, **antes** de seleccionar la página.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from tests.api.support import walk


def items(world, client, query: str = "") -> list[dict]:
    response = client.get(f"{world.base}/product-overviews{('?' + query) if query else ''}")
    assert response.status_code == 200, response.text
    return response.json()["items"]


def test_with_and_without_image(world, as_user) -> None:
    """CP-10, CP-11 y CP-14: la URL es la de PC-1, sin cambios; sin imagen, `image_url = null`."""
    with_image = world.product("Con imagen", has_image=True)
    without = world.product("Sin imagen")
    found = {item["company_product_id"]: item for item in items(world, as_user("ventas.test"))}
    expected_url = world.fakes.pc.products[with_image.product.global_product_id].image_url
    assert found[with_image.id]["has_image"] is True and found[with_image.id]["image_url"] == expected_url
    assert found[without.id]["has_image"] is False and found[without.id]["image_url"] is None


def test_has_image_true_and_false_filters(world, as_user) -> None:
    """CP-12 y CP-13."""
    with_image = world.product("Con imagen", has_image=True)
    without = world.product("Sin imagen")
    client = as_user("ventas.test")
    assert [i["company_product_id"] for i in items(world, client, "has_image=true")] == [with_image.id]
    assert [i["company_product_id"] for i in items(world, client, "has_image=false")] == [without.id]


def test_has_image_false_never_carries_a_url(world, as_user) -> None:
    """FR-022-45: aunque PC enviara una URL con `has_image = false`, la respuesta no la expone."""
    item = world.product("Inconsistente")
    summary = world.fakes.pc.products[item.product.global_product_id]
    world.fakes.pc.products[summary.id] = replace(summary, image_url="https://pc.test/x")
    found = items(world, as_user("ventas.test"))[0]
    assert found["has_image"] is False and found["image_url"] is None


def test_filter_is_applied_before_selecting_the_page(world, as_user) -> None:
    """FR-022-48 y CP-20: con 30 productos y solo los últimos 8 con imagen, la primera página trae 5 con imagen."""
    created = [world.product(f"Producto {index:02d}", has_image=index >= 22) for index in range(30)]
    client = as_user("ventas.test")
    first = items(world, client, "has_image=true&page_size=5")
    assert [i["display_name"] for i in first] == [f"Producto {index:02d}" for index in range(22, 27)]
    assert all(i["has_image"] for i in first)

    walked, _ = walk(client, f"{world.base}/product-overviews?has_image=true&page_size=3")
    assert [i["company_product_id"] for i in walked] == [item.id for item in created[22:]]


def test_has_image_combined_with_brand_and_search(world, as_user) -> None:
    """CP-19 y escenario 2 de la historia 1: solo marca y con imagen; todas exactamente una vez al recorrer."""
    brand = uuid4()
    expected = []
    for index in range(26):
        item = world.product(f"Colgate {index:02d}", brand=brand if index % 2 == 0 else uuid4(), has_image=index % 3 != 0)
        if index % 2 == 0 and index % 3 != 0:
            expected.append(item.id)
    walked, pages = walk(as_user("ventas.test"),
                         f"{world.base}/product-overviews?search=Colgate&brand_id={brand}&has_image=true&page_size=4")
    assert [i["company_product_id"] for i in walked] == expected
    assert len(walked) == len(set(i["company_product_id"] for i in walked))
    assert all(page["sort_applied"] == "display_name:asc" for page in pages)


def test_image_filter_is_evaluated_by_product_catalog_on_the_candidates_only(world, as_user) -> None:
    """CP-91: `search=Colgate&has_image=true` → CR conduce y PC evalúa solo los candidatos del lote."""
    for index in range(3):
        world.product(f"Colgate {index}", has_image=True)
    world.product("Otra marca", has_image=True)
    items(world, as_user("ventas.test"), "search=Colgate&has_image=true")
    log = world.fakes.log
    assert log.order.index("search_products") < log.order.index("match_candidates")
    ((_, arguments),) = [key for key in log.calls if key[0] == "match_candidates"]
    assert len(arguments[1]) == 3  # solo los 3 candidatos de CR, no el catálogo completo
    assert log.count("match_page") == 0
