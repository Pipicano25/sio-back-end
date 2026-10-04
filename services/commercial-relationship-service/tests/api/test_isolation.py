"""Historia 5: aislamiento por empresa en las rutas con empresa (RC-02, RC-03; FR-040 a FR-045; SC-002).

Se crea un recurso de cada tipo en una empresa y se recorre cada ruta con un
usuario con permiso pero sin membresía activa: debe responder `404` con el mismo
cuerpo que un UUID inexistente, incluso con cuerpo inválido, sin cambios y sin
llamar a Product Catalog ni a Party Identity. `admin.test` (`perm:all:all:all`)
no se exime (DS-03).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.helpers import adopt, person_customer, supplier
from tests.api.routes import ROUTES, route_id
from tests.conftest import user_sub


@pytest.fixture
def resources(as_user, company, fake_catalog, fake_party):
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog)
    customer = person_customer(client, company, fake_party)
    provider = supplier(client, company, fake_party)
    return {"product": product, "customer": customer, "supplier": provider}


def _url(route, company, resources, *, missing=False):
    ids = {
        "company_id": str(uuid4() if missing else company),
        "company_product_id": str(uuid4() if missing else resources["product"]["id"]),
        "company_customer_id": str(uuid4() if missing else resources["customer"]["id"]),
        "company_supplier_id": str(uuid4() if missing else resources["supplier"]["id"]),
    }
    return route.path.format(**ids)


def _call(client, route, url, body):
    if route.method == "GET":
        return client.get(url)
    return client.request(route.method, url, json=body)


def _snapshot(as_user, company):
    client = as_user("admin.test")
    return {
        kind: client.get(f"/api/v1/companies/{company}/company-{kind}", params={"status": "ALL"}).json()["items"]
        for kind in ("products", "customers", "suppliers")
    }


# Lotes y resumen no tienen empresa en la ruta: su aislamiento se prueba aparte
# (lotes en este archivo, resumen en `test_company_summaries.py`).
ISOLATED = [route for route in ROUTES if route.target not in {"batch", "summary"}]


@pytest.mark.parametrize("route", ISOLATED, ids=route_id)
@pytest.mark.parametrize("username", ["admin.test", "supervisor.test"])
def test_non_member_gets_404_like_missing_uuid(as_user, company, fake_oc, fake_catalog, fake_party, resources, route, username):
    before = _snapshot(as_user, company)
    fake_oc.deactivate_member(user_sub(username), company)
    client = as_user(username)
    lookups, first_uses, party_calls = (
        len(fake_catalog.lookup_calls), len(fake_catalog.first_use_calls), len(fake_party.calls)
    )

    response = _call(client, route, _url(route, company, resources), {"basura": True})

    if route.action == "delete" and username == "supervisor.test":
        assert response.status_code == 403  # sin permiso, antes que el alcance
        return

    assert response.status_code == 404, response.text
    missing = _call(client, route, _url(route, company, resources, missing=True), {"basura": True})
    assert missing.status_code == 404
    strip = {"trace_id", "instance"}
    assert {k: v for k, v in response.json().items() if k not in strip} == {
        k: v for k, v in missing.json().items() if k not in strip
    }
    assert (len(fake_catalog.lookup_calls), len(fake_catalog.first_use_calls), len(fake_party.calls)) == (
        lookups, first_uses, party_calls
    )

    fake_oc.add_member(user_sub("admin.test"), company)
    assert _snapshot(as_user, company) == before


def test_batch_lookup_hides_foreign_products(as_user, company, fake_oc, resources):
    fake_oc.deactivate_member(user_sub("consulta.test"), company)
    response = as_user("consulta.test").post(
        "/api/v1/company-products/batch-lookup", json={"ids": [resources["product"]["id"]]}
    )
    assert response.status_code == 200
    [item] = response.json()["items"]
    assert item["id"] == resources["product"]["id"]
    assert item["found"] is False
    # Ningún dato del producto ajeno se revela.
    assert all(value is None for key, value in item.items() if key not in {"id", "found"})


@pytest.mark.parametrize("route", [r for r in ISOLATED if not r.write], ids=route_id)
def test_inactive_company_allows_reads(as_user, company, fake_oc, resources, route):
    fake_oc.inactive_companies.add(company)
    response = _call(as_user("consulta.test"), route, _url(route, company, resources), None)
    assert response.status_code == 200, response.text


def test_inactive_company_blocks_writes_except_deactivate(as_user, company, fake_oc, resources):
    fake_oc.inactive_companies.add(company)
    client = as_user("admin.test")
    for route in (r for r in ISOLATED if r.write):
        response = _call(client, route, _url(route, company, resources), {"version": 1})
        if route.allows_inactive_company:
            assert response.status_code == 200, (route_id(route), response.text)
            assert response.json()["status"] == "INACTIVE"
        else:
            assert response.status_code == 422, route_id(route)
            assert response.json()["code"] == "COMMERCIAL_RELATIONSHIP.COMPANY_INACTIVE", route_id(route)


@pytest.mark.parametrize("route", ISOLATED, ids=route_id)
def test_operational_context_unavailable_is_503(as_user, company, fake_oc, resources, route):
    fake_oc.access_unavailable = True
    response = _call(as_user("admin.test"), route, _url(route, company, resources), {"version": 1})
    assert response.status_code == 503
    assert response.json()["dependency"] == "operational-context"


@pytest.mark.parametrize("route", ISOLATED, ids=route_id)
def test_operational_context_forbidden_is_403(as_user, company, fake_oc, resources, route):
    fake_oc.access_forbidden = True
    response = _call(as_user("admin.test"), route, _url(route, company, resources), {"version": 1})
    assert response.status_code == 403
    assert response.json()["code"] == "COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED"


def test_membership_is_evaluated_on_every_request(as_user, company, fake_oc, resources):
    client = as_user("consulta.test")
    url = f"/api/v1/company-products/{resources['product']['id']}"
    assert client.get(url).status_code == 200
    fake_oc.deactivate_member(user_sub("consulta.test"), company)
    assert client.get(url).status_code == 404
    fake_oc.add_member(user_sub("consulta.test"), company)
    assert client.get(url).status_code == 200
