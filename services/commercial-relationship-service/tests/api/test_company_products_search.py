"""CR-1: búsqueda progresiva de productos empresariales (spec 022, FR-022-80; T014).

`POST /companies/{company_id}/company-products/search`: filtros del listado, SKU de presentación,
`internal_code` y `sku` exactos, orden estable con desempate por `id`, continuación *keyset*
(`after` + `limit`, `has_more` sin conteo) y modo evaluador por ids. No cambia el listado `GET`.
"""

from __future__ import annotations

from uuid import uuid4

from tests.api.helpers import adopt, adopt_presentation
from tests.conftest import LOOKUP

URL = "/api/v1/companies/{company}/company-products/search"
READ = "perm:commercial-relationship:company_products:read"


def _search(client, company, **body):
    body.setdefault("limit", 100)
    response = client.post(URL.format(company=company), json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _ids(page) -> list[str]:
    return [item["id"] for item in page["items"]]


def _walk(client, company, limit: int, **body) -> list[str]:
    """Recorre todas las páginas con `after`; falla si una vuelta no avanza."""
    seen: list[str] = []
    after = None
    for _ in range(100):
        page = _search(client, company, limit=limit, **({"after": after} if after else {}), **body)
        seen.extend(_ids(page))
        if not page["has_more"]:
            return seen
        after = page["items"][-1]["position"]
    raise AssertionError("la búsqueda no terminó")


def test_response_has_no_totals_and_carries_position(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog, internal_code="A1", display_name="Alfa")

    page = _search(client, company)
    assert set(page) == {"items", "has_more"}
    assert page["has_more"] is False
    item = page["items"][0]
    assert item["id"] == product["id"]
    assert item["global_product_id"] == product["global_product_id"]
    assert item["position"] == {"k": ["Alfa"], "id": product["id"]}
    # Mismos campos que el listado actual, más la posición.
    listed = client.get(f"/api/v1/companies/{company}/company-products").json()["items"][0]
    assert set(item) - {"position"} == set(listed)


def test_filters_status_default_active_and_flags(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    active = adopt(client, company, fake_catalog, internal_code="A", display_name="Activo")
    inactive = adopt(client, company, fake_catalog, internal_code="I", display_name="Inactivo")
    untracked = adopt(client, company, fake_catalog, internal_code="U", display_name="Sin control", inventory_control_enabled=False)
    client.post(f"/api/v1/company-products/{inactive['id']}/deactivate", json={"version": 1})

    assert set(_ids(_search(client, company))) == {active["id"], untracked["id"]}
    assert _ids(_search(client, company, status="INACTIVE")) == [inactive["id"]]
    assert len(_ids(_search(client, company, status="ALL"))) == 3
    assert _ids(_search(client, company, inventory_control_enabled=True)) == [active["id"]]


def test_search_covers_name_codes_and_presentation_sku_without_duplicates(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    by_name = adopt(client, company, fake_catalog, internal_code="000045", display_name="Crema Colgate 100 ml")
    by_reference = adopt(client, company, fake_catalog, internal_code="000046", display_name="Otro", reference_code="REF-COL")
    by_sku = adopt(client, company, fake_catalog, internal_code="000047", display_name="Cepillo")
    adopt_presentation(client, company, fake_catalog, by_sku, sku="SKU-COLG-1")
    adopt_presentation(client, company, fake_catalog, by_sku, sku="SKU-COLG-2")
    adopt(client, company, fake_catalog, internal_code="000048", display_name="Leche")

    found = _ids(_search(client, company, search="col"))
    assert sorted(found) == sorted([by_name["id"], by_reference["id"], by_sku["id"]])
    assert len(found) == len(set(found)), "dos presentaciones no duplican el producto"
    assert _ids(_search(client, company, search="0000")) != []


def test_internal_code_and_sku_are_exact(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    target = adopt(client, company, fake_catalog, internal_code="ABC-1", display_name="Uno")
    adopt(client, company, fake_catalog, internal_code="ABC-10", display_name="Diez")
    adopt_presentation(client, company, fake_catalog, target, sku="77SKU")

    assert _ids(_search(client, company, internal_code="abc-1")) == [target["id"]]
    assert _ids(_search(client, company, sku="77sku")) == [target["id"]]
    assert _ids(_search(client, company, sku="77")) == []


def test_keyset_walk_with_ties_has_no_gaps_or_duplicates(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    created = [
        adopt(client, company, fake_catalog, internal_code=f"T{index:02d}", display_name=name)
        for index, name in enumerate(["Beta", "Alfa", "Beta", "Beta", "Gamma", "Alfa", "Delta"])
    ]
    expected = [p["id"] for p in sorted(created, key=lambda p: (p["display_name"], p["id"]))]

    for limit in (1, 2, 3, 7):
        assert _walk(client, company, limit) == expected

    descending = list(reversed(expected))
    assert _walk(client, company, 2, sort={"key": "display_name", "direction": "desc"}) == descending


def test_sort_by_internal_code_and_created_at(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    created = [adopt(client, company, fake_catalog, internal_code=code, display_name="Igual") for code in ("C", "A", "B")]

    by_code = _walk(client, company, 1, sort={"key": "internal_code", "direction": "asc"})
    assert by_code == [p["id"] for p in sorted(created, key=lambda p: (p["internal_code"], p["id"]))]

    by_date = _walk(client, company, 2, sort={"key": "created_at", "direction": "asc"})
    assert by_date == [p["id"] for p in sorted(created, key=lambda p: (p["created_at"], p["id"]))]


def test_evaluator_mode_with_company_or_global_ids(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    a = adopt(client, company, fake_catalog, internal_code="EA", display_name="Alfa")
    b = adopt(client, company, fake_catalog, internal_code="EB", display_name="Beta", is_sellable=False)
    adopt(client, company, fake_catalog, internal_code="EC", display_name="Gamma")

    assert _ids(_search(client, company, company_product_ids=[b["id"], a["id"]])) == [a["id"], b["id"]]
    assert _ids(_search(client, company, global_product_ids=[b["global_product_id"], str(uuid4())])) == [b["id"]]
    # Los filtros se aplican también en modo evaluador.
    assert _ids(_search(client, company, company_product_ids=[a["id"], b["id"]], is_sellable=False)) == [b["id"]]


def test_validation_errors(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    url = URL.format(company=company)
    ids = [str(uuid4())]
    cases = [
        {"limit": 0},
        {"limit": 101},
        {},
        {"limit": 10, "company_product_ids": ids, "global_product_ids": ids},
        {"limit": 10, "company_product_ids": [str(uuid4()) for _ in range(101)]},
        {"limit": 10, "after": {"k": ["Alfa"]}},
        {"limit": 10, "sort": {"key": "created_at", "direction": "asc"}, "after": {"k": ["no-es-fecha"], "id": ids[0]}},
        {"limit": 10, "sort": {"key": "price", "direction": "asc"}},
        {"limit": 10, "unknown": True},
        {"limit": 10, "status": "BLOCKED"},
    ]
    for body in cases:
        response = client.post(url, json=body)
        assert response.status_code == 422, (body, response.text)


def test_other_company_is_404_and_permission_is_required(as_user, as_token, make_token, company, other_company) -> None:
    assert as_user("admin.test").post(URL.format(company=other_company), json={"limit": 5}).status_code == 404
    assert as_user("inventario.test").post(URL.format(company=company), json={"limit": 5}).status_code == 403
    assert as_token(None).post(URL.format(company=company), json={"limit": 5}).status_code == 401


def test_technical_identity_with_platform_lookup(as_user, as_token, service_token, company, fake_catalog) -> None:
    product = adopt(as_user("admin.test"), company, fake_catalog, internal_code="TEC", display_name="Técnico")
    technical = as_token(service_token(READ, LOOKUP, client_id="product-inventory-query-service"))
    response = technical.post(URL.format(company=company), json={"limit": 5})
    assert response.status_code == 200, response.text
    assert _ids(response.json()) == [product["id"]]

    # Sin platform:lookup, la cuenta técnica no es miembro de la empresa.
    without_lookup = as_token(service_token(READ, client_id="product-inventory-query-service"))
    assert without_lookup.post(URL.format(company=company), json={"limit": 5}).status_code == 404


def test_listing_get_is_unchanged(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    adopt(client, company, fake_catalog, internal_code="L1", display_name="Uno")
    page = client.get(f"/api/v1/companies/{company}/company-products").json()
    assert set(page) == {"items", "page", "page_size", "total_records", "total_pages"}
    assert page["total_records"] == 1
