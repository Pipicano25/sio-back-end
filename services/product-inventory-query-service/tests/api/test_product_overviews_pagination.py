"""Paginación de `product-overviews` por API (T102; FR-022-60 a FR-022-67, FR-022-149 a FR-022-151).

CP-71 a CP-78, los reinicios CP-110 a CP-115 y CP-120 de la sección "Ejemplos de paginación" y los cursores
alterados, de otra empresa y de otro endpoint (CP-116, CP-118, CP-119).
"""

from __future__ import annotations

import time

import pytest

from product_inventory_query_service.domain.cursor import CursorCodec, Expected
from tests.api.support import walk
from tests.conftest import TEST_CURSOR_SECRET


def get(world, client, query: str = "", endpoint: str = "product-overviews"):
    return client.get(f"{world.base}/{endpoint}{('?' + query) if query else ''}")


def page(world, client, query: str = "", endpoint: str = "product-overviews") -> dict:
    response = get(world, client, query, endpoint)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def colgate(world):
    """25 válidos de 40 candidatos de CR (ejemplo de la spec): 40 «Colgate», 25 con imagen."""
    return [world.product(f"Colgate {index:02d}", has_image=index < 25) for index in range(40)]


def test_first_second_and_last_page(world, as_user, colgate) -> None:
    """CP-71, CP-72 y CP-73: 20, después los 5 sobrantes del lote anterior y `has_next = false`."""
    client = as_user("ventas.test")
    first = page(world, client, "search=Colgate&has_image=true")
    assert len(first["items"]) == 20 and first["has_next"] and first["next_cursor"]
    assert (first["pagination_reset"], first["pagination_reset_reason"], first["partial"]) == (False, None, False)
    assert set(first) == {"items", "page_size", "has_next", "next_cursor", "pagination_reset",
                          "pagination_reset_reason", "partial", "partial_reason", "sort_applied", "resolved_at"}

    second = page(world, client, f"search=Colgate&has_image=true&cursor={first['next_cursor']}")
    assert [i["display_name"] for i in second["items"]] == [f"Colgate {index:02d}" for index in range(20, 25)]
    assert second["has_next"] is False and second["next_cursor"] is None
    assert not {i["company_product_id"] for i in first["items"]} & {i["company_product_id"] for i in second["items"]}


def test_exact_last_page(world, as_user) -> None:
    """CP-134 por API: exactamente `page_size` válidos y conductor agotado → `has_next = false`."""
    for index in range(20):
        world.product(f"P {index:02d}")
    body = page(world, as_user("ventas.test"))
    assert len(body["items"]) == 20 and body["has_next"] is False and body["next_cursor"] is None


@pytest.mark.parametrize("size", [1, 5, 10, 15, 20])
def test_page_sizes_and_never_more_than_page_size(world, as_user, size) -> None:
    """CP-75 y CP-77: el lote es `min(max(page_size × 2, 20), 40)`; nunca más de `page_size` items."""
    for index in range(45):
        world.product(f"P {index:02d}")
    body = page(world, as_user("ventas.test"), f"page_size={size}")
    assert len(body["items"]) == size and body["page_size"] == size
    ((_, arguments),) = [key for key in world.fakes.log.calls if key[0] == "search_products"]
    assert arguments[4] == min(max(size * 2, 20), 40)  # `limit` del conductor


@pytest.mark.parametrize("value", ["0", "21", "-1", "uno", "1.5"])
def test_page_size_out_of_range_is_422(world, as_user, value) -> None:
    """CP-76."""
    response = get(world, as_user("ventas.test"), f"page_size={value}")
    assert response.status_code == 422
    assert response.json()["code"] == "PRODUCT_INVENTORY_QUERY.VALIDATION_ERROR"
    assert world.fakes.log.total() == 0  # nada se consulta antes de validar


def test_unknown_parameter_is_422(world, as_user) -> None:
    """CP-124."""
    response = get(world, as_user("ventas.test"), "color=rojo")
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "UNKNOWN_FIELD"


def test_stable_order_with_ties_resolved_by_id(world, as_user) -> None:
    """CP-78 y CP-133: nombres repetidos de a tres, sin omisiones ni duplicados al recorrer."""
    created = [world.product(f"Repetido {index // 3:02d}") for index in range(30)]
    walked, _ = walk(as_user("ventas.test"), f"{world.base}/product-overviews?page_size=4")
    expected = sorted(created, key=lambda item: (item.product.display_name, str(item.product.id)))
    assert [i["company_product_id"] for i in walked] == [item.id for item in expected]


@pytest.mark.parametrize(
    ("changed", "reason"),
    [
        ("search=Abrilar&has_image=true", "FILTERS_CHANGED"),
        ("search=Colgate&has_image=false", "FILTERS_CHANGED"),
        ("search=Colgate&has_image=true&page_size=10", "PAGE_SIZE_CHANGED"),
        ("search=Colgate&has_image=true&sort=internal_code", "SORT_CHANGED"),
    ],
)
def test_changes_reset_to_the_first_page_with_the_reason(world, as_user, colgate, changed, reason) -> None:
    """CP-112 a CP-115 y FR-022-150: primera página de los parámetros actuales, nunca un error."""
    world.product("Abrilar jarabe", has_image=True)
    client = as_user("ventas.test")
    cursor = page(world, client, "search=Colgate&has_image=true")["next_cursor"]
    body = page(world, client, f"{changed}&cursor={cursor}")
    assert body["pagination_reset"] is True and body["pagination_reset_reason"] == reason
    fresh = page(world, client, changed)
    assert body["items"] == fresh["items"]
    if reason == "PAGE_SIZE_CHANGED":
        assert len(body["items"]) == 10


def test_continuation_with_the_same_filters_is_not_a_reset(world, as_user, colgate) -> None:
    """CP-111: el orden de los parámetros, espacios y mayúsculas de `search` no cambian la huella (CP-122)."""
    client = as_user("ventas.test")
    cursor = page(world, client, "search=Colgate&has_image=true")["next_cursor"]
    body = page(world, client, f"has_image=true&search=%20%20colgate%20&cursor={cursor}")
    assert body["pagination_reset"] is False and len(body["items"]) == 5


def test_explicit_default_sort_on_a_cr_route_is_the_same_cursor(world, as_user, colgate) -> None:
    """FR-022-65: en R-B omitir `sort` o enviar `display_name:asc` da lo mismo."""
    client = as_user("ventas.test")
    cursor = page(world, client, "search=Colgate&has_image=true")["next_cursor"]
    body = page(world, client, f"search=Colgate&has_image=true&sort=display_name:asc&cursor={cursor}")
    assert body["pagination_reset"] is False


def test_altered_cursor_is_422_without_results(world, as_user, colgate) -> None:
    """CP-116."""
    client = as_user("ventas.test")
    cursor = page(world, client, "search=Colgate&has_image=true")["next_cursor"]
    altered = cursor[:-3] + ("A" if cursor[-3] != "A" else "B") + cursor[-2:]
    response = get(world, client, f"search=Colgate&has_image=true&cursor={altered}")
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "PRODUCT_INVENTORY_QUERY.INVALID_CURSOR" and "items" not in body


def test_cursor_of_another_company_and_of_another_endpoint_are_422(world, as_user, colgate) -> None:
    """CP-118 y CP-119: mismo mensaje que un cursor alterado."""
    other, _ = world.fakes.oc.add_company(branches=1)  # el usuario también es miembro de la otra empresa
    for index in range(25):
        world.product(f"Colgate B{index:02d}", has_image=True, company=other)
    client = as_user("ventas.test")
    foreign = client.get(f"/api/v1/companies/{other}/product-overviews?search=Colgate&has_image=true").json()
    response = get(world, client, f"search=Colgate&has_image=true&cursor={foreign['next_cursor']}")
    assert response.status_code == 422 and response.json()["code"] == "PRODUCT_INVENTORY_QUERY.INVALID_CURSOR"

    cursor = page(world, client, "search=Colgate&has_image=true")["next_cursor"]
    elsewhere = get(world, client, f"search=Colgate&has_image=true&cursor={cursor}", endpoint="inventory-overviews")
    assert elsewhere.status_code == 422
    assert elsewhere.json()["detail"] == response.json()["detail"]


def test_expired_cursor_restarts_with_cursor_expired(world, as_user, colgate) -> None:
    """CP-120 y CP-144: firma válida y vencido → primera página con los filtros actuales."""
    client = as_user("ventas.test")
    valid = page(world, client, "search=Colgate&has_image=true")["next_cursor"]
    payload = CursorCodec(TEST_CURSOR_SECRET).decode(valid)
    old = CursorCodec(TEST_CURSOR_SECRET, clock=lambda: time.time() - 3600)
    expected = Expected(payload.ep, payload.cid, payload.fh, payload.sort, payload.ps, payload.route)
    expired = old.issue(expected, kind=payload.k, position=payload.pos)
    body = page(world, client, f"search=Colgate&has_image=true&cursor={expired}")
    assert body["pagination_reset"] is True and body["pagination_reset_reason"] == "CURSOR_EXPIRED"
    assert len(body["items"]) == 20


def test_cursor_has_no_tokens_or_id_lists(world, as_user, colgate) -> None:
    """CP-126: el contenido solo lleva la posición del último entregado."""
    client = as_user("ventas.test")
    cursor = page(world, client, "search=Colgate&has_image=true")["next_cursor"]
    payload = CursorCodec(TEST_CURSOR_SECRET).decode(cursor).to_json()
    assert set(payload["pos"]) == {"k", "id"} and payload["k"] == "PAGE"
    text = str(payload)
    assert "Bearer" not in text and "sub-ventas.test" not in text and "perm:" not in text
    assert not any(isinstance(value, list) and len(value) > 1 for value in payload["pos"].values())


def test_work_limit_returns_partial_scan_and_continues_without_losses(world, as_user) -> None:
    """CP-99, CP-100 y CP-142 por API: 1.000 candidatos y 4 válidos → parciales hasta el final, sin pérdidas."""
    expected = []
    for index in range(1000):
        item = world.product(f"A {index:04d}", has_image=index % 300 == 0)
        if index % 300 == 0:
            expected.append(item.id)
    client = as_user("ventas.test")
    first = page(world, client, "search=A&has_image=true")
    assert first["partial"] is True and first["partial_reason"] == "WORK_LIMIT_REACHED" and first["has_next"]
    assert len(first["items"]) == 1  # 5 lotes de 40 = 200 candidatos: solo la posición 0
    walked, pages = walk(client, f"{world.base}/product-overviews?search=A&has_image=true")
    assert [i["company_product_id"] for i in walked] == expected
    assert any(p["partial"] and not p["items"] for p in pages)
    assert pages[-1]["has_next"] is False
