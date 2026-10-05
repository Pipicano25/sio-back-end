"""Historia 1 de la 010: adoptar y mantener presentaciones empresariales (T024; FR-010 a FR-017).

Cubre los escenarios 1–10, colecciones con filtros, `PUT` (inmutables, marcas,
idéntico), estados y el desmarcado atómico con versión y auditoría (aclaración 4).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from tests.api.helpers import (
    adopt,
    adopt_presentation,
    code_of,
    global_presentation,
    presentation_update_body,
)
from tests.conftest import user_sub

URL = "/api/v1/companies/{company}/company-product-presentations"


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


@pytest.fixture
def product(admin, company, fake_catalog):
    return adopt(admin, company, fake_catalog)


def _post(client, company, body):
    return client.post(URL.format(company=company), json=body)


def test_scenario_1_adopts_with_defaults_and_registers_first_use(admin, company, fake_catalog, product):
    presentation = global_presentation(fake_catalog, product)
    response = _post(admin, company, {
        "company_product_id": product["id"], "global_product_presentation_id": str(presentation), "sku": "CJ12-001",
    })

    assert response.status_code == 201, response.text
    body = response.json()
    assert response.headers["Location"] == f"/api/v1/company-product-presentations/{body['id']}"
    assert body["status"] == "ACTIVE" and body["version"] == 1
    assert body["is_purchasable"] and body["is_sellable"]
    assert not body["is_default_purchase"] and not body["is_default_sale"]
    assert body["company_id"] == str(company) and body["sku"] == "CJ12-001"
    assert body["created_by"] == body["updated_by"] == user_sub("admin.test")
    assert (fake_catalog.presentation_first_use_calls[-1][1]) == presentation
    assert "name" not in body and "base_quantity" not in body  # sin datos de la presentación global


def test_scenario_2_presentation_of_other_global_product(admin, company, fake_catalog, product):
    other = fake_catalog.add_presentation(uuid4(), uuid4())
    response = _post(admin, company, {"company_product_id": product["id"], "global_product_presentation_id": str(other)})

    assert response.status_code == 422
    assert code_of(response) == "GLOBAL_PRESENTATION_OF_OTHER_PRODUCT"
    assert fake_catalog.presentation_first_use_calls == []


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        (None, "GLOBAL_PRESENTATION_NOT_FOUND"),
        ({"status": "INACTIVE"}, "GLOBAL_PRESENTATION_INACTIVE"),
        ({"eligible": False}, "GLOBAL_PRESENTATION_NOT_ELIGIBLE"),
    ],
)
def test_scenario_3_global_presentation_causes(admin, company, fake_catalog, product, kwargs, code):
    presentation = uuid4() if kwargs is None else global_presentation(fake_catalog, product, **kwargs)
    response = _post(admin, company, {"company_product_id": product["id"], "global_product_presentation_id": str(presentation)})

    assert response.status_code == 422
    assert code_of(response) == code
    assert response.json()["errors"][0]["field"] == "global_product_presentation_id"


def test_scenario_4_duplicate_adoption_in_any_state_without_first_use(admin, company, fake_catalog, product):
    created = adopt_presentation(admin, company, fake_catalog, product)
    admin.post(f"/api/v1/company-product-presentations/{created['id']}/deactivate", json={"version": 1})
    calls = len(fake_catalog.presentation_first_use_calls)

    response = _post(admin, company, {
        "company_product_id": product["id"], "global_product_presentation_id": created["global_product_presentation_id"],
    })

    assert response.status_code == 409
    assert code_of(response) == "DUPLICATE_PRESENTATION_ADOPTION"
    assert len(fake_catalog.presentation_first_use_calls) == calls


@pytest.mark.parametrize("field", ["sku", "internal_code"])
def test_scenario_5_codes_unique_per_company_case_insensitive(admin, company, fake_catalog, product, field):
    adopt_presentation(admin, company, fake_catalog, product, **{field: "cj12-001"})
    other_product = adopt(admin, company, fake_catalog, internal_code="000046")

    response = _post(admin, company, {
        "company_product_id": other_product["id"],
        "global_product_presentation_id": str(global_presentation(fake_catalog, other_product)),
        field: "CJ12-001",
    })

    assert response.status_code == 409
    assert code_of(response) == ("DUPLICATE_SKU" if field == "sku" else "DUPLICATE_INTERNAL_CODE")


def test_scenario_6_inactive_or_foreign_company_product(admin, company, other_company, fake_catalog, product):
    admin.post(f"/api/v1/company-products/{product['id']}/deactivate", json={"version": 1})
    response = _post(admin, company, {
        "company_product_id": product["id"], "global_product_presentation_id": str(global_presentation(fake_catalog, product)),
    })
    assert response.status_code == 422 and code_of(response) == "COMPANY_PRODUCT_INACTIVE"

    response = _post(admin, company, {"company_product_id": str(uuid4()), "global_product_presentation_id": str(uuid4())})
    assert response.status_code == 422 and code_of(response) == "COMPANY_PRODUCT_NOT_FOUND"


@pytest.mark.parametrize("failure", ["lookup", "first_use"])
def test_scenario_7_product_catalog_unavailable_persists_nothing(admin, company, fake_catalog, product, failure):
    if failure == "lookup":
        fake_catalog.presentation_lookup_unavailable = True
    else:
        fake_catalog.first_use_error = "unavailable"

    response = _post(admin, company, {
        "company_product_id": product["id"], "global_product_presentation_id": str(global_presentation(fake_catalog, product)),
    })

    assert response.status_code == 503
    assert response.json()["dependency"] == "product-catalog"
    listed = admin.get(URL.format(company=company), params={"status": "ALL"}).json()
    assert listed["total_records"] == 0


def test_scenario_8_default_purchase_swaps_atomically(admin, company, fake_catalog, product):
    first = adopt_presentation(admin, company, fake_catalog, product, is_default_purchase=True)
    second = adopt_presentation(admin, company, fake_catalog, product)

    response = admin.put(
        f"/api/v1/company-product-presentations/{second['id']}",
        json=presentation_update_body(second, is_default_purchase=True),
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_default_purchase"] is True
    previous = admin.get(f"/api/v1/company-product-presentations/{first['id']}").json()
    assert previous["is_default_purchase"] is False
    assert previous["version"] == first["version"] + 1
    assert previous["updated_by"] == user_sub("admin.test")

    third = adopt_presentation(admin, company, fake_catalog, product, is_default_purchase=True)
    assert admin.get(f"/api/v1/company-product-presentations/{second['id']}").json()["is_default_purchase"] is False
    assert third["is_default_purchase"] is True


def test_scenario_9_default_requires_flag(admin, company, fake_catalog, product):
    response = _post(admin, company, {
        "company_product_id": product["id"], "global_product_presentation_id": str(global_presentation(fake_catalog, product)),
        "is_purchasable": False, "is_default_purchase": True,
    })
    assert response.status_code == 422 and code_of(response) == "DEFAULT_FLAG_INVALID"


def test_scenario_10_deactivate_clears_default_and_reactivate_without_mark(admin, company, fake_catalog, product):
    created = adopt_presentation(admin, company, fake_catalog, product, is_default_sale=True)
    url = f"/api/v1/company-product-presentations/{created['id']}"

    deactivated = admin.post(url + "/deactivate", json={"version": 1}).json()
    assert deactivated["status"] == "INACTIVE" and deactivated["is_default_sale"] is False

    reactivated = admin.post(url + "/reactivate", json={"version": deactivated["version"]}).json()
    assert reactivated["status"] == "ACTIVE" and reactivated["is_default_sale"] is False
    assert len(fake_catalog.presentation_first_use_calls) == 1  # solo al adoptar


def test_reactivate_requires_active_global_presentation(admin, company, fake_catalog, product):
    created = adopt_presentation(admin, company, fake_catalog, product)
    url = f"/api/v1/company-product-presentations/{created['id']}"
    admin.post(url + "/deactivate", json={"version": 1})
    fake_catalog.add_presentation(
        UUID(created["global_product_presentation_id"]), UUID(product["global_product_id"]), status="INACTIVE"
    )

    response = admin.post(url + "/reactivate", json={"version": 2})
    assert response.status_code == 422 and code_of(response) == "GLOBAL_PRESENTATION_INACTIVE"


def test_put_rules(admin, company, fake_catalog, product):
    created = adopt_presentation(admin, company, fake_catalog, product, is_default_purchase=True, sku="A-1")
    url = f"/api/v1/company-product-presentations/{created['id']}"

    for field in ("company_product_id", "global_product_presentation_id"):
        response = admin.put(url, json={**presentation_update_body(created), field: str(uuid4())})
        assert response.status_code == 422 and code_of(response) == "IMMUTABLE_FIELD"

    same = admin.put(url, json=presentation_update_body(created))
    assert same.status_code == 200 and same.json()["version"] == 1  # idéntico: sin incremento

    stale = admin.put(url, json=presentation_update_body(created, sku="A-2", version=99))
    assert stale.status_code == 409 and code_of(stale) == "VERSION_CONFLICT"

    # Desmarcar la bandera desmarca la predeterminada correspondiente (FR-014).
    unmarked = admin.put(url, json=presentation_update_body(created, is_purchasable=False))
    assert unmarked.status_code == 200, unmarked.text
    assert unmarked.json()["is_default_purchase"] is False

    deactivated = admin.post(url + "/deactivate", json={"version": unmarked.json()["version"]}).json()
    marked_inactive = admin.put(url, json=presentation_update_body(deactivated, is_default_sale=True))
    assert marked_inactive.status_code == 422 and code_of(marked_inactive) == "DEFAULT_REQUIRES_ACTIVE"

    edited_inactive = admin.put(url, json=presentation_update_body(deactivated, reference_code="REF-9"))
    assert edited_inactive.status_code == 200 and edited_inactive.json()["status"] == "INACTIVE"


def test_list_filters_search_and_default_status(admin, company, fake_catalog, product):
    other_product = adopt(admin, company, fake_catalog, internal_code="000046")
    first = adopt_presentation(admin, company, fake_catalog, product, sku="CAJA-12", is_sellable=False)
    adopt_presentation(admin, company, fake_catalog, other_product, internal_code="UND-1")
    admin.post(f"/api/v1/company-product-presentations/{first['id']}/deactivate", json={"version": 1})
    url = URL.format(company=company)

    assert admin.get(url).json()["total_records"] == 1  # sin estado: solo ACTIVE
    assert admin.get(url, params={"status": "ALL"}).json()["total_records"] == 2
    assert admin.get(url, params={"status": "ALL", "search": "caja"}).json()["items"][0]["id"] == first["id"]
    assert admin.get(url, params={"status": "ALL", "company_product_id": product["id"]}).json()["total_records"] == 1
    assert admin.get(url, params={"status": "ALL", "is_sellable": "false"}).json()["total_records"] == 1
    assert admin.get(
        url, params={"global_product_presentation_id": first["global_product_presentation_id"], "status": "ALL"}
    ).json()["total_records"] == 1


@pytest.mark.parametrize("username", ["consulta.test", "reportes.test", "ventas.test", "compras.test"])
def test_readers_can_read_but_not_write(as_user, admin, company, fake_catalog, product, username):
    created = adopt_presentation(admin, company, fake_catalog, product)
    client = as_user(username)

    assert client.get(f"/api/v1/company-product-presentations/{created['id']}").status_code == 200
    response = _post(client, company, {"company_product_id": product["id"], "global_product_presentation_id": str(uuid4())})
    assert response.status_code == 403


def test_supervisor_cannot_deactivate(as_user, admin, company, fake_catalog, product):
    created = adopt_presentation(admin, company, fake_catalog, product)
    response = as_user("supervisor.test").post(
        f"/api/v1/company-product-presentations/{created['id']}/deactivate", json={"version": 1}
    )
    assert response.status_code == 403


def test_inventory_user_has_no_access(as_user, company):
    assert as_user("inventario.test").get(URL.format(company=company)).status_code == 403
