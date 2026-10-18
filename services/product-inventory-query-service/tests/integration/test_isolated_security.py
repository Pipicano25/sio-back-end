"""Seguridad con servicios reales en la pila aislada (T145; SC-022-3, SC-022-5, SC-022-9).

Matriz por grupo, otra empresa, cursores alterados y de otra empresa, `ref` alterada, ausencia de listado público
de imágenes y logs de los contenedores `sio-it-*` sin tokens, cursores ni referencias de imagen.
"""

from __future__ import annotations

import re

import pytest

from tests.integration.support import PC, PIQ, anonymous_client, container_logs

pytestmark = pytest.mark.integration

ENDPOINTS = ("product-overviews", "inventory-overviews", "low-stock-products", "inventory-summary")
MATRIX = {
    "admin.test": (200, 200, 200, 200),
    "supervisor.test": (200, 200, 200, 200),
    "ventas.test": (200, 200, 403, 403),
    "inventario.test": (200, 200, 200, 200),
    "compras.test": (403, 403, 403, 403),
    "reportes.test": (403, 403, 403, 403),
    "consulta.test": (403, 403, 403, 403),
}
COSTS = re.compile(r"inventory_value|average_unit_cost|unit_cost|margin|fifo|valuation", re.IGNORECASE)


@pytest.mark.parametrize("username", list(MATRIX))
def test_matrix_per_group_with_real_keycloak_tokens(users, seed, username) -> None:
    client = users(username)
    for endpoint, expected in zip(ENDPOINTS, MATRIX[username], strict=True):
        response = client.get(f"{PIQ}/companies/{seed['company']}/{endpoint}", params={} if endpoint == "inventory-summary" else {"page_size": "5"})
        assert response.status_code == expected, (username, endpoint, response.text[:200])
        assert not COSTS.search(response.text), (username, endpoint)
        if response.status_code == 403:
            assert "perm:" not in response.text
        if endpoint == "product-overviews" and expected == 200:
            items = response.json()["items"]
            has_price = any("price" in p for i in items for p in i["presentations"])
            assert has_price == (username != "inventario.test"), username  # inventario no ve precios
            has_minimums = any("minimum_state" in b for i in items for b in (i.get("stock") or {}).get("branches", []))
            assert has_minimums == (username != "ventas.test"), username  # ventas no ve mínimos


def test_no_token_and_forged_token_are_401(seed) -> None:
    with anonymous_client() as client:
        for headers in ({}, {"Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.e30.firma"}):
            response = client.get(f"{PIQ}/companies/{seed['company']}/product-overviews", headers=headers)
            assert response.status_code == 401


def test_other_company_never_leaks(users, seed) -> None:
    """`inventario.test` no es miembro de la empresa B: `404`, sin datos; con `ventas.test` (miembro) solo filas de B."""
    assert users("inventario.test").get(f"{PIQ}/companies/{seed['other_company']}/product-overviews").status_code == 404
    items = users("ventas.test").get(f"{PIQ}/companies/{seed['other_company']}/product-overviews",
                                     params={"page_size": "20"}).raise_for_status().json()["items"]
    own = {p["company_product_id"] for p in seed["products"].values()}
    assert items and not {i["company_product_id"] for i in items} & own


def test_altered_cursor_is_422(users, seed) -> None:
    ventas = users("ventas.test")
    base = f"{PIQ}/companies/{seed['company']}/product-overviews"
    cursor = ventas.get(base, params={"page_size": "2"}).raise_for_status().json()["next_cursor"]
    altered = cursor[:-2] + ("AA" if not cursor.endswith("AA") else "BB")
    response = ventas.get(base, params={"page_size": "2", "cursor": altered})
    assert response.status_code == 422 and response.json()["code"] == "PRODUCT_INVENTORY_QUERY.INVALID_CURSOR"


def test_public_image_reference_is_signed_and_not_listable(users, seed) -> None:
    (item,) = users("ventas.test").get(f"{PIQ}/companies/{seed['company']}/product-overviews",
                                       params={"internal_code": f"P-0001-{seed['run']}"}).raise_for_status().json()["items"]
    url = item["image_url"]
    assert url.startswith("http://127.0.0.1:18103/api/v1/public/product-images?ref=")
    ref = url.split("ref=", 1)[1]
    altered = ref[:-1] + ("A" if ref[-1] != "A" else "B")
    with anonymous_client() as browser:
        good = browser.get(url)
        assert good.status_code == 200
        for header, value in (("x-content-type-options", "nosniff"), ("cross-origin-resource-policy", "cross-origin")):
            assert good.headers[header] == value
        assert good.headers["etag"] and "s3://" not in str(good.headers) and "assets/" not in str(good.headers)
        for probe in (f"{PC}/public/product-images?ref={altered}", f"{PC}/public/product-images",
                      f"{url}&page=1", f"{PC}/public/product-images/list"):
            response = browser.get(probe)
            assert response.status_code in (401, 404), (probe, response.status_code)
            assert not response.content.startswith(b"\x89PNG")


def test_container_logs_have_no_tokens_cursors_or_refs(users, seed) -> None:
    """Después de las consultas anteriores, ningún log de la pila aislada contiene secretos de sesión."""
    ventas = users("ventas.test")
    ventas.get(f"{PIQ}/companies/{seed['company']}/product-overviews", params={"page_size": "2"})
    patterns = (re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"), re.compile(r"v1\.eyJ[A-Za-z0-9_-]{20,}"),
                re.compile(r"ref=[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"))
    for name in ("sio-it-product-inventory-query-service", "sio-it-product-catalog-service",
                 "sio-it-commercial-relationship-service", "sio-it-inventory-service"):
        logs = container_logs(name)
        assert logs.strip(), name
        for pattern in patterns:
            assert not pattern.search(logs), f"{name}: {pattern.pattern}"
