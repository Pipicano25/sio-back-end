"""Recorrido con los servicios reales de la pila aislada (T133; quickstart §3).

OC, CR, PC, Inventory y Keycloak reales: token del usuario, membresía, permisos, token técnico, aislamiento,
serialización y paginación. Las páginas se comparan con consultas **directas** a los servicios propietarios.
"""

from __future__ import annotations

import pytest

from tests.integration.support import CR, PC, PIQ, anonymous_client, stop_and_restore, walk

pytestmark = pytest.mark.integration

ECONOMIC = ("inventory_value", "average_unit_cost", "unit_cost", "margin", "fifo", "valuation")


def text_has_no_costs(text: str) -> None:
    assert not any(word in text for word in ECONOMIC), text[:300]


def direct_search(admin, seed, *, search=None, has_image=None) -> list[str]:
    """CR-1 (orden de `display_name`) y PC-2 en modo evaluador: la referencia que los propietarios calculan."""
    body = {"status": "ACTIVE", "sort": {"key": "display_name", "direction": "asc"}, "limit": 100}
    if search:
        body["search"] = search
    rows, after = [], None
    while True:
        page = admin.post(f"{CR}/companies/{seed['company']}/company-products/search",
                          json={**body, **({"after": after} if after else {})}).raise_for_status().json()
        rows.extend(page["items"])
        if not page["has_more"]:
            break
        after = page["items"][-1]["position"]
    if has_image is None:
        return [row["id"] for row in rows]
    accepted = set()
    for start in range(0, len(rows), 100):
        chunk = rows[start:start + 100]
        result = admin.post(f"{PC}/products/match", json={
            "status": "ALL", "has_image": has_image, "candidate_ids": [row["global_product_id"] for row in chunk]})
        accepted |= set(result.raise_for_status().json()["ids"])
    return [row["id"] for row in rows if row["global_product_id"] in accepted]


def test_r_b_search_with_image_walk_equals_the_owners(users, seed) -> None:
    """R-B: CR busca y PC evalúa la imagen; el recorrido completo coincide con la consulta directa."""
    ventas, admin = users("ventas.test"), users("admin.test")
    items, pages = walk(ventas, f"/companies/{seed['company']}/product-overviews",
                        [("search", "Colgate"), ("has_image", "true"), ("page_size", "1")])
    assert [i["company_product_id"] for i in items] == direct_search(admin, seed, search="Colgate", has_image=True)
    # Spec 024: la imagen es de la presentación (la primera del producto sembrado).
    assert items and all(any(p["has_image"] and p["image_url"] for p in i["presentations"]) for i in items)
    assert {p["sort_applied"] for p in pages} == {"display_name:asc"}
    text_has_no_costs(str(pages))


def test_r_c_brand_conducted_by_catalog_excludes_not_adopted(users, seed) -> None:
    """R-C: PC conduce por marca; CR traduce y descarta los productos globales que la empresa no adoptó."""
    ventas = users("ventas.test")
    items, pages = walk(ventas, f"/companies/{seed['company']}/product-overviews",
                        [("brand_id", seed["brands"]["COLGATE"]), ("page_size", "2")])
    expected = {p["company_product_id"] for p in seed["products"].values() if p["brand"] == "COLGATE"}
    assert {i["company_product_id"] for i in items} == expected
    assert len(items) == len(expected)
    assert not {i["global_product_id"] for i in items} & set(seed["not_adopted"])
    assert {p["sort_applied"] for p in pages} == {"canonical_name:asc"}


def test_prices_and_currency_come_from_commercial_relationship(users, seed) -> None:
    """Precio y moneda de CR; sin precio, `unit_price` y `currency_code` son `null`; una sola lista."""
    ventas = users("ventas.test")
    triple = seed["products"]["Crema dental Colgate Triple Acción 100 ml"]
    base = f"{PIQ}/companies/{seed['company']}/product-overviews"
    (item,) = ventas.get(base, params={"internal_code": f"P-0001-{seed['run']}"}).raise_for_status().json()["items"]
    prices = {p["company_product_presentation_id"]: p["price"] for p in item["presentations"]}
    unit, box = (prices[row["id"]] for row in triple["presentations"])
    assert (unit["unit_price"], unit["currency_code"], unit["resolution"]) == ("4500.00", "COP", "PRICE_LIST_ITEM")
    assert unit["price_list_id"] == seed["default_price_list"]
    assert (box["unit_price"], box["currency_code"]) == (None, None) and box["resolution"] != "PRICE_LIST_ITEM"

    other = ventas.get(base, params={"internal_code": f"P-0001-{seed['run']}", "price_list_id": seed["other_price_list"]})
    prices = {p["company_product_presentation_id"]: p["price"] for p in other.raise_for_status().json()["items"][0]["presentations"]}
    assert prices[triple["presentations"][0]["id"]]["unit_price"] == "4100.00"
    assert prices[triple["presentations"][1]["id"]]["unit_price"] is None


def test_inventory_multibranch_registered_zero_and_not_registered(users, seed) -> None:
    """Consolidado, saldo 0 registrado, sin registro, equivalencias sin duplicar y mínimos solo con el permiso."""
    inventario, ventas = users("inventario.test"), users("ventas.test")
    params = {"internal_code": f"P-0007-{seed['run']}"}  # Loratadina: PPAL 120, NORTE 0 registrado, SUR sin saldo
    (item,) = inventario.get(f"{PIQ}/companies/{seed['company']}/inventory-overviews", params=params).raise_for_status().json()["items"]
    branches = {b["branch_id"]: b for b in item["stock"]["branches"]}
    ppal, norte, sur = (branches[seed["branches"][code]] for code in ("PPAL", "NORTE", "SUR"))
    assert (ppal["base_quantity"], ppal["balance_state"], ppal["minimum_state"]) == ("120.0000", "REGISTERED", "BELOW_MINIMUM")
    assert (norte["base_quantity"], norte["balance_state"]) == ("0.0000", "REGISTERED")
    assert (sur["base_quantity"], sur["balance_state"], sur["minimum_state"]) == ("0.0000", "NOT_REGISTERED", "NO_POLICY")
    assert item["stock"]["total_base_quantity"] == "120.0000"
    box = seed["products"]["Loratadina 10 mg tabletas"]["presentations"][1]["id"]
    equivalence = next(e for e in item["stock"]["equivalences"] if e["company_product_presentation_id"] == box)
    assert (equivalence["whole_units"], equivalence["remainder_base_quantity"]) == (12, "0.0000")

    (seen,) = ventas.get(f"{PIQ}/companies/{seed['company']}/inventory-overviews", params=params).raise_for_status().json()["items"]
    assert all("minimum_state" not in b for b in seen["stock"]["branches"])


def test_branch_without_assignment_is_readable_a08(users, seed) -> None:
    """`inventario.test` está asignado solo a PPAL y consulta NORTE."""
    response = users("inventario.test").get(f"{PIQ}/companies/{seed['company']}/inventory-overviews",
                                            params={"branch_id": seed["branches"]["NORTE"], "page_size": "20"})
    assert response.status_code == 200, response.text
    assert all(b["branch_id"] == seed["branches"]["NORTE"] for i in response.json()["items"] for b in i["stock"]["branches"])


def test_low_stock_pairs(users, seed) -> None:
    items, pages = walk(users("inventario.test"), f"/companies/{seed['company']}/low-stock-products", [("page_size", "1")])
    pairs = [(i["display_name"], i["branch_id"], i["shortfall"]) for i in items]
    assert pairs == [
        ("Loratadina 10 mg tabletas", seed["branches"]["PPAL"], "30.0000"),
        *sorted([("Acetaminofén 500 mg tabletas", seed["branches"]["NORTE"], "2.0000"),
                 ("Crema dental Colgate Kids 50 ml", seed["branches"]["SUR"], "2.0000")],
                key=lambda row: next(p["company_product_id"] for n, p in seed["products"].items() if n == row[0])),
    ]
    assert {p["sort_applied"] for p in pages} == {"shortfall:desc"}


def test_summary_is_operational_and_owned_by_each_service(users, seed) -> None:
    body = users("inventario.test").get(f"{PIQ}/companies/{seed['company']}/inventory-summary").raise_for_status().json()
    assert body["adopted_products"] == 33  # ACTIVE y con control: excluye el servicio y el producto inactivo
    branches = {b["branch_id"]: b for b in body["branches"]}
    assert branches[seed["branches"]["PPAL"]] == {"branch_id": seed["branches"]["PPAL"], "products_with_positive_balance": 17,
                                                  "products_with_zero_balance": 1, "products_with_policy": 4,
                                                  "products_below_minimum": 1}
    assert branches[seed["branches"]["NORTE"]]["products_with_zero_balance"] == 1
    assert branches[seed["branches"]["SUR"]] == {"branch_id": seed["branches"]["SUR"], "products_with_positive_balance": 0,
                                                 "products_with_zero_balance": 0, "products_with_policy": 1,
                                                 "products_below_minimum": 1}
    assert body["consolidated"] == {"products_with_positive_balance": 17, "products_with_zero_balance": 1,
                                    "products_with_policy": 5, "products_below_minimum": 3}
    supervisor = users("supervisor.test").get(f"{PIQ}/companies/{seed['company']}/inventory-summary").raise_for_status()
    text_has_no_costs(supervisor.text)
    assert "currency_code" not in supervisor.json()


def test_cursor_reset_and_cursor_of_another_company(users, seed) -> None:
    ventas = users("ventas.test")
    base = f"{PIQ}/companies/{seed['company']}/product-overviews"
    first = ventas.get(base, params={"search": "Producto ficticio", "page_size": "3"}).raise_for_status().json()
    reset = ventas.get(base, params={"search": "Colgate", "page_size": "3", "cursor": first["next_cursor"]}).raise_for_status().json()
    assert (reset["pagination_reset"], reset["pagination_reset_reason"]) == (True, "FILTERS_CHANGED")
    sort = ventas.get(base, params={"search": "Producto ficticio", "page_size": "3", "sort": "internal_code:desc",
                                    "cursor": first["next_cursor"]}).raise_for_status().json()
    assert sort["pagination_reset_reason"] == "SORT_CHANGED" and sort["sort_applied"] == "internal_code:desc"

    foreign = ventas.get(f"{PIQ}/companies/{seed['other_company']}/product-overviews",
                         params={"search": "Colgate", "page_size": "1"}).raise_for_status().json()
    assert foreign["items"] and all(i["company_product_id"] in seed["products_b"] for i in foreign["items"])
    response = ventas.get(base, params={"search": "Colgate", "page_size": "1", "cursor": foreign["next_cursor"]})
    assert response.status_code == 422 and response.json()["code"] == "PRODUCT_INVENTORY_QUERY.INVALID_CURSOR"


def test_image_url_without_token_200_then_304(users, seed) -> None:
    (item,) = users("ventas.test").get(f"{PIQ}/companies/{seed['company']}/product-overviews",
                                       params={"internal_code": f"P-0001-{seed['run']}"}).raise_for_status().json()["items"]
    url = next(p["image_url"] for p in item["presentations"] if p["has_image"])
    with anonymous_client() as browser:
        first = browser.get(url)
        assert first.status_code == 200 and first.headers["content-type"] == "image/png"
        assert first.content.startswith(b"\x89PNG") and first.headers["cache-control"] == "public, max-age=31536000, immutable"
        again = browser.get(url, headers={"If-None-Match": first.headers["etag"]})
        assert again.status_code == 304 and again.content == b""


def test_403_for_groups_without_permission_and_404_for_other_company(users, seed) -> None:
    for name in ("compras.test", "reportes.test", "consulta.test"):
        for path in ("product-overviews", "inventory-overviews", "low-stock-products", "inventory-summary"):
            response = users(name).get(f"{PIQ}/companies/{seed['company']}/{path}")
            assert response.status_code == 403 and "perm:" not in response.text, (name, path)
    assert users("inventario.test").get(f"{PIQ}/companies/{seed['other_company']}/inventory-overviews").status_code == 404
    assert users("ventas.test").get(f"{PIQ}/companies/{seed['company']}/product-overviews",
                                    params={"branch_id": seed["branch_b"]}).status_code == 404


def test_inventory_down_is_503_never_an_empty_list(users, seed) -> None:
    ventas = users("ventas.test")
    restore = stop_and_restore("sio-it-inventory-service")
    try:
        response = ventas.get(f"{PIQ}/companies/{seed['company']}/product-overviews", params={"stock_state": "IN_STOCK"})
        assert response.status_code == 503
        assert response.json()["code"] == "PRODUCT_INVENTORY_QUERY.DEPENDENCY_UNAVAILABLE" and "items" not in response.json()
    finally:
        restore()
    assert ventas.get(f"{PIQ}/companies/{seed['company']}/product-overviews",
                      params={"stock_state": "IN_STOCK"}).status_code == 200


def test_summary_is_isolated_per_company(users, seed) -> None:
    """Aislamiento empresarial del resumen: la empresa B solo cuenta sus productos; un no miembro recibe `404`."""
    assert users("inventario.test").get(f"{PIQ}/companies/{seed['other_company']}/inventory-summary").status_code == 404
    body = users("admin.test").get(f"{PIQ}/companies/{seed['other_company']}/inventory-summary").raise_for_status().json()
    assert body["company_id"] == seed["other_company"]
    assert body["adopted_products"] == len(seed["products_b"])  # 3, nunca los 33 de la empresa A
    assert [b["branch_id"] for b in body["branches"]] == [seed["branch_b"]]
    assert body["consolidated"]["products_with_positive_balance"] == 0
