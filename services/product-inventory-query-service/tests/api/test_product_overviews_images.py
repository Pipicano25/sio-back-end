"""Imágenes en `product-overviews` e `inventory-overviews` (specs 022 y 024; FR-024-40 a FR-024-44, casos 24 y 25).

Spec 024: la imagen es de cada **presentación**. Cada presentación trae `has_image`, `asset_id` e `image_url` de su
imagen principal, tal como los calcula Product Catalog en `presentations/batch-lookup` (PC-3), y `images[]` solo
con `include_images=true`. El producto ya no tiene campos de imagen. El filtro `has_image` sigue siendo una
condición de búsqueda resuelta por PC-2 ("al menos una presentación con imagen principal `ACTIVE`", DD-024-3) y
se aplica sobre los candidatos **antes** de seleccionar la página.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest

from tests.api.support import walk

ENDPOINTS = ["product-overviews", "inventory-overviews"]


def body(world, client, query: str = "", endpoint: str = "product-overviews") -> dict:
    response = client.get(f"{world.base}/{endpoint}{('?' + query) if query else ''}")
    assert response.status_code == 200, response.text
    return response.json()


def items(world, client, query: str = "", endpoint: str = "product-overviews") -> list[dict]:
    return body(world, client, query, endpoint)["items"]


def by_code(item: dict) -> dict:
    return {presentation["code"]: presentation for presentation in item["presentations"]}


TWO = (("UND", "Unidad", "1"), ("CJ12", "Caja x 12", "12"))


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_image_fields_are_per_presentation_and_images_are_omitted_by_default(world, as_user, endpoint) -> None:
    """Caso 24: sin `include_images`, cada presentación trae su principal y no trae `images`."""
    item = world.product("Crema", presentations=TWO, has_image=True)
    found = by_code(items(world, as_user("supervisor.test"), endpoint=endpoint)[0])
    unit, box = found["UND"], found["CJ12"]
    info = world.fakes.pc.presentation_rows[item.global_presentations[0]]
    assert (unit["has_image"], unit["asset_id"], unit["image_url"]) == (True, str(info.image_asset_id), info.image_url)
    assert (box["has_image"], box["asset_id"], box["image_url"]) == (False, None, None)
    assert "images" not in unit and "images" not in box
    product = items(world, as_user("supervisor.test"), endpoint=endpoint)[0]
    assert not {"has_image", "asset_id", "image_url"} & set(product)


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_include_images_adds_all_active_images_with_the_primary_first(world, as_user, endpoint) -> None:
    """Caso 25: `images[]` por presentación, la principal primero; una presentación sin imágenes trae `[]`."""
    item = world.product("Crema", presentations=TWO, has_image=True)
    secondary = world.fakes.pc.add_image(item.global_presentations[0], primary=False)
    primary = world.fakes.pc.presentation_rows[item.global_presentations[0]]

    found = by_code(items(world, as_user("supervisor.test"), "include_images=true", endpoint)[0])

    assert found["UND"]["images"] == [
        {"asset_id": str(primary.image_asset_id), "image_url": primary.image_url, "is_primary": True},
        {"asset_id": str(secondary.asset_id), "image_url": secondary.image_url, "is_primary": False},
    ]
    assert found["CJ12"]["images"] == [] and found["CJ12"]["has_image"] is False


def test_include_images_uses_the_same_batch_calls(world, as_user) -> None:
    """FR-024-42: las mismas llamadas por lotes con y sin `include_images` (sin consultas por fila)."""
    for index in range(5):
        world.product(f"Producto {index}", presentations=TWO, has_image=True)
    client = as_user("ventas.test")
    log = world.fakes.log

    items(world, client)
    without = log.count("presentations")
    log.calls.clear()
    items(world, client, "include_images=true")
    assert log.count("presentations") == without == 1
    ((_, (_ids, include_images)),) = [key for key in log.calls if key[0] == "presentations"]
    assert include_images is True


def test_include_images_is_not_part_of_the_cursor(world, as_user) -> None:
    """FR-024-41: cambiar `include_images` entre páginas no reinicia la paginación."""
    for index in range(5):
        world.product(f"Producto {index}", has_image=True)
    client = as_user("ventas.test")
    first = body(world, client, "page_size=2")
    second = body(world, client, f"page_size=2&include_images=true&cursor={first['next_cursor']}")
    assert second["pagination_reset"] is False
    assert [i["display_name"] for i in second["items"]] == ["Producto 2", "Producto 3"]
    assert all("images" in p for i in second["items"] for p in i["presentations"])


def test_has_image_filter_means_any_presentation_with_a_primary_image(world, as_user) -> None:
    """DD-024-3: basta una presentación con imagen principal, aunque no sea la primera."""
    second_only = world.product("Solo la caja", presentations=TWO)
    world.fakes.pc.add_image(second_only.global_presentations[1])
    without = world.product("Sin imagen")
    client = as_user("ventas.test")
    assert [i["company_product_id"] for i in items(world, client, "has_image=true")] == [second_only.id]
    assert [i["company_product_id"] for i in items(world, client, "has_image=false")] == [without.id]
    found = by_code(items(world, client, "has_image=true")[0])
    assert (found["UND"]["has_image"], found["CJ12"]["has_image"]) == (False, True)


def test_has_image_false_never_carries_a_url(world, as_user) -> None:
    """Aunque PC enviara una URL con `has_image = false`, la respuesta no la expone."""
    item = world.product("Inconsistente")
    presentation = item.global_presentations[0]
    info = world.fakes.pc.presentation_rows[presentation]
    world.fakes.pc.presentation_rows[presentation] = replace(info, image_url="https://pc.test/x", image_asset_id=uuid4())
    found = items(world, as_user("ventas.test"))[0]["presentations"][0]
    assert (found["has_image"], found["asset_id"], found["image_url"]) == (False, None, None)


def test_include_images_must_be_boolean(world, as_user) -> None:
    response = as_user("ventas.test").get(f"{world.base}/product-overviews?include_images=quizas")
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "include_images"


def test_filter_is_applied_before_selecting_the_page(world, as_user) -> None:
    """FR-022-48 y CP-20: con 30 productos y solo los últimos 8 con imagen, la primera página trae 5 con imagen."""
    created = [world.product(f"Producto {index:02d}", has_image=index >= 22) for index in range(30)]
    client = as_user("ventas.test")
    first = items(world, client, "has_image=true&page_size=5")
    assert [i["display_name"] for i in first] == [f"Producto {index:02d}" for index in range(22, 27)]
    assert all(any(p["has_image"] for p in i["presentations"]) for i in first)

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
