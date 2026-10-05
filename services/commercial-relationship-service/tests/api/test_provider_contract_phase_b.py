"""Contrato Provider ampliado de la Fase B (T068; FR-080 a FR-084; RC-03, RC-13).

Mismas reglas que la Fase A (`test_provider_contract.py`, que fija que su
contrato no cambia): exención técnica solo con cuenta de servicio y
`platform:lookup`, solo lectura.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.helpers import (
    adopt,
    adopt_presentation,
    code_of,
    create_condition,
    create_price,
    create_price_list,
    create_supplier_product,
    supplier,
)
from tests.conftest import LOOKUP, user_sub

READ = {kind: f"perm:commercial-relationship:{resource}:read" for kind, resource in {
    "presentation": "company_product_presentations",
    "supplier_product": "supplier_products",
    "condition": "supplier_payment_conditions",
    "price_list": "price_lists",
    "price": "price_list_items",
}.items()}
PATH = {
    "presentation": "/api/v1/company-product-presentations/{id}",
    "supplier_product": "/api/v1/supplier-products/{id}",
    "condition": "/api/v1/supplier-payment-conditions/{id}",
    "price_list": "/api/v1/price-lists/{id}",
    "price": "/api/v1/price-list-items/{id}",
}
GUARANTEED = {
    "presentation": {"id", "company_id", "company_product_id", "global_product_presentation_id", "is_purchasable",
                     "is_sellable", "is_default_purchase", "is_default_sale", "status", "version"},
    "supplier_product": {"id", "company_id", "company_supplier_id", "company_product_id", "company_product_presentation_id",
                         "purchase_unit_id", "minimum_order_quantity", "pack_quantity", "negotiated_unit_cost",
                         "currency_code", "expected_supplier_lead_time_hours", "is_preferred", "status", "version"},
    "condition": {"id", "company_id", "company_supplier_id", "payment_condition_type_id", "currency_code",
                  "payment_terms_days", "credit_limit", "interest_rate_percentage", "cash_discount_percentage",
                  "is_default", "valid_from", "valid_to", "status", "version"},
    "price_list": {"id", "company_id", "code", "currency_code", "is_default", "valid_from", "valid_to", "status", "version"},
    "price": {"id", "company_id", "price_list_id", "company_product_id", "company_product_presentation_id",
              "unit_price", "currency_code", "valid_from", "valid_to", "status", "version"},
}
KINDS = sorted(PATH)


@pytest.fixture
def resources(as_user, company, fake_catalog, fake_party, fake_payment):
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog)
    provider = supplier(client, company, fake_party)
    price_list = create_price_list(client, company)
    return {
        "product": product,
        "presentation": adopt_presentation(client, company, fake_catalog, product),
        "supplier_product": create_supplier_product(client, company, provider, product, fake_catalog),
        "condition": create_condition(client, company, provider, fake_payment),
        "price_list": price_list,
        "price": create_price(client, company, price_list, product),
    }


@pytest.fixture
def no_members(fake_oc):
    fake_oc.members.clear()
    fake_oc.access_calls.clear()


@pytest.mark.parametrize("kind", KINDS)
def test_service_account_with_lookup_reads_guaranteed_fields(resources, no_members, as_token, service_token, fake_oc, kind):
    response = as_token(service_token(READ[kind], LOOKUP)).get(PATH[kind].format(id=resources[kind]["id"]))
    assert response.status_code == 200, response.text
    assert GUARANTEED[kind] <= set(response.json())
    assert fake_oc.access_calls == []


@pytest.mark.parametrize("kind", KINDS)
def test_reads_in_any_state(as_user, resources, as_token, service_token, kind):
    item = resources[kind]
    as_user("admin.test").post(PATH[kind].format(id=item["id"]) + "/deactivate", json={"version": item["version"]})
    response = as_token(service_token(READ[kind], LOOKUP)).get(PATH[kind].format(id=item["id"]))
    assert response.status_code == 200 and response.json()["status"] == "INACTIVE"


@pytest.mark.parametrize("kind", KINDS)
def test_without_lookup_isolation_applies(resources, no_members, as_token, service_token, fake_oc, kind):
    url = PATH[kind].format(id=resources[kind]["id"])
    assert as_token(service_token(READ[kind])).get(url).status_code == 404
    fake_oc.access_forbidden = True
    response = as_token(service_token(READ[kind])).get(url)
    assert response.status_code == 403 and code_of(response) == "OPERATIONAL_ACCESS_DENIED"


@pytest.mark.parametrize("kind", KINDS)
def test_human_with_all_all_all_without_membership_is_404(resources, as_user, fake_oc, company, kind):
    fake_oc.deactivate_member(user_sub("admin.test"), company)
    assert as_user("admin.test").get(PATH[kind].format(id=resources[kind]["id"])).status_code == 404


@pytest.mark.parametrize("kind", KINDS)
def test_lookup_never_authorizes_writes(resources, no_members, as_token, service_token, kind):
    token = service_token(READ[kind], LOOKUP, f"perm:commercial-relationship:{READ[kind].split(':')[2]}:update")
    response = as_token(token).post(PATH[kind].format(id=resources[kind]["id"]) + "/reactivate", json={"version": 1})
    assert response.status_code == 404  # sin membresía: la capacidad no exime en escrituras


def test_presentation_batch_lookup(as_user, company, other_company, fake_catalog, resources, no_members, as_token, service_token, fake_oc):
    known = resources["presentation"]["id"]
    ids = [known, known, str(uuid4())]

    response = as_token(service_token(READ["presentation"], LOOKUP)).post(
        "/api/v1/company-product-presentations/batch-lookup", json={"ids": ids}
    )
    assert response.status_code == 200, response.text
    found, missing = response.json()["items"]  # duplicados ignorados
    assert found["found"] is True and GUARANTEED["presentation"] <= set(found)
    assert missing["found"] is False and all(value is None for key, value in missing.items() if key not in {"id", "found"})

    # Un humano sin membresía ve la presentación como no encontrada.
    human = as_user("consulta.test").post("/api/v1/company-product-presentations/batch-lookup", json={"ids": [known]})
    assert human.json()["items"][0]["found"] is False

    too_many = as_token(service_token(READ["presentation"], LOOKUP)).post(
        "/api/v1/company-product-presentations/batch-lookup", json={"ids": [str(uuid4()) for _ in range(101)]}
    )
    assert too_many.status_code == 422 and code_of(too_many) == "BATCH_LIMIT_EXCEEDED"


def test_applicable_price_with_technical_identity(company, resources, no_members, as_token, service_token, fake_oc):
    response = as_token(service_token(READ["price"], LOOKUP)).post(
        f"/api/v1/companies/{company}/applicable-prices/resolve",
        json={"lines": [{"company_product_id": resources["product"]["id"], "price_list_id": resources["price_list"]["id"]}]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["resolution"] == "PRICE_LIST_ITEM"
    assert fake_oc.access_calls == []
