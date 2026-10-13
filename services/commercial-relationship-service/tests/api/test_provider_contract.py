"""Contrato Provider (RC-11; FR-060 a FR-063; contracts/commercial-relationship-provider.md).

Exención técnica (R-11): cuenta de servicio coherente (`client_id` +
`preferred_username = service-account-{client_id}`) **y** `platform:lookup`.
Solo lectura; orden de evaluación permiso → alcance → escritura.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.helpers import adopt, code_of, person_customer, product_update_body, supplier
from tests.conftest import LOOKUP, user_sub

READ = {
    "product": "perm:commercial-relationship:company_products:read",
    "customer": "perm:commercial-relationship:company_customers:read",
    "supplier": "perm:commercial-relationship:company_suppliers:read",
}
PATH = {
    "product": "/api/v1/company-products/{id}",
    "customer": "/api/v1/company-customers/{id}",
    "supplier": "/api/v1/company-suppliers/{id}",
}
GUARANTEED = {
    "product": {"id", "company_id", "global_product_id", "internal_code", "display_name", "currency_code",
                "inventory_control_enabled", "lot_tracking_enabled", "expiration_tracking_enabled",
                "is_purchasable", "is_sellable", "status", "version"},
    "customer": {"id", "company_id", "customer_kind", "person_identity_id", "organization_identity_id",
                 "internal_code", "display_name", "status", "version"},
    "supplier": {"id", "company_id", "organization_identity_id", "internal_code", "display_name", "status",
                 "block_reason", "version"},
}


@pytest.fixture
def resources(as_user, company, fake_catalog, fake_party):
    client = as_user("admin.test")
    return {
        "product": adopt(client, company, fake_catalog),
        "customer": person_customer(client, company, fake_party),
        "supplier": supplier(client, company, fake_party),
    }


@pytest.fixture
def no_members(fake_oc, company):
    """Nadie es miembro: solo la exención técnica permite leer."""
    fake_oc.members.clear()
    fake_oc.access_calls.clear()


@pytest.mark.parametrize("kind", ["product", "customer", "supplier"])
def test_service_account_with_lookup_reads_without_membership(resources, no_members, as_token, service_token, fake_oc, kind):
    token = service_token(READ[kind], LOOKUP)
    response = as_token(token).get(PATH[kind].format(id=resources[kind]["id"]))
    assert response.status_code == 200, response.text
    assert GUARANTEED[kind] <= set(response.json())
    assert fake_oc.access_calls == []  # la exención no consulta Operational Context


@pytest.mark.parametrize("kind", ["product", "customer", "supplier"])
def test_reads_in_any_state(as_user, resources, as_token, service_token, kind):
    action = "deactivate"
    item = resources[kind]
    as_user("admin.test").post(f"{PATH[kind].format(id=item['id'])}/{action}", json={"version": item["version"]})
    response = as_token(service_token(READ[kind], LOOKUP)).get(PATH[kind].format(id=item["id"]))
    assert response.status_code == 200 and response.json()["status"] == "INACTIVE"


@pytest.mark.parametrize("kind", ["product", "customer", "supplier"])
def test_service_account_without_lookup_is_isolated(resources, no_members, as_token, service_token, fake_oc, kind):
    url = PATH[kind].format(id=resources[kind]["id"])
    token = service_token(READ[kind])

    response = as_token(token).get(url)
    assert response.status_code == 404  # Operational Context responde USER_NOT_MEMBER

    fake_oc.access_forbidden = True
    response = as_token(token).get(url)
    assert response.status_code == 403
    assert code_of(response) == "OPERATIONAL_ACCESS_DENIED"


@pytest.mark.parametrize("kind", ["product", "customer", "supplier"])
def test_human_with_all_all_all_without_membership_is_404(resources, as_user, fake_oc, company, kind):
    fake_oc.deactivate_member(user_sub("admin.test"), company)
    assert as_user("admin.test").get(PATH[kind].format(id=resources[kind]["id"])).status_code == 404


def test_incoherent_claims_do_not_exempt(resources, no_members, as_token, make_token):
    url = PATH["product"].format(id=resources["product"]["id"])
    human_named_like_sa = make_token(READ["product"], LOOKUP, sub="h", preferred_username="service-account-x")
    mismatch = make_token(READ["product"], LOOKUP, sub="m", client_id="x", preferred_username="service-account-y", sid=None)
    assert as_token(human_named_like_sa).get(url).status_code == 404
    assert as_token(mismatch).get(url).status_code == 404


def test_errors(as_token, service_token):
    token = service_token(READ["product"], LOOKUP)
    assert as_token(token).get(PATH["product"].format(id=uuid4())).status_code == 404
    malformed = as_token(token).get(PATH["product"].format(id="no-es-uuid"))
    assert malformed.status_code == 422 and code_of(malformed) == "VALIDATION_ERROR"
    assert as_token(None).get(PATH["product"].format(id=uuid4())).status_code == 401
    assert as_token(service_token(LOOKUP)).get(PATH["product"].format(id=uuid4())).status_code == 403


def test_lookup_does_not_authorize_writes(resources, no_members, as_token, service_token, fake_oc):
    product = resources["product"]
    url = PATH["product"].format(id=product["id"])
    body = product_update_body(product, display_name="Intento")

    # Solo lectura + lookup: 403 por permiso, sin llamar a Operational Context.
    read_only = as_token(service_token(READ["product"], LOOKUP))
    for response in (
        read_only.put(url, json=body),
        read_only.post(f"{url}/deactivate", json={"version": 1}),
        read_only.post(f"{url}/reactivate", json={"version": 1}),
    ):
        assert response.status_code == 403
    assert fake_oc.access_calls == []

    # Con permiso de escritura: la exención no aplica y se evalúa el alcance normal.
    writer = as_token(service_token(READ["product"], LOOKUP, "perm:commercial-relationship:company_products:update"))
    assert writer.put(url, json=body).status_code == 404
    fake_oc.access_forbidden = True
    response = writer.put(url, json=body)
    assert response.status_code == 403 and code_of(response) == "OPERATIONAL_ACCESS_DENIED"


def test_unchanged_after_rejected_write(as_user, resources, no_members, as_token, service_token, fake_oc, company):
    product = resources["product"]
    writer = as_token(service_token(READ["product"], LOOKUP, "perm:commercial-relationship:company_products:update"))
    writer.put(PATH["product"].format(id=product["id"]), json=product_update_body(product, display_name="X"))
    fake_oc.add_member(user_sub("admin.test"), company)
    current = as_user("admin.test").get(PATH["product"].format(id=product["id"])).json()
    assert current["version"] == product["version"] and current["updated_at"] == product["updated_at"]


# --------------------------------------------------------------------- lotes


def test_batch_lookup_with_exemption(as_user, company, fake_catalog, resources, no_members, as_token, service_token, fake_oc):
    first = resources["product"]["id"]
    missing = str(uuid4())
    response = as_token(service_token(READ["product"], LOOKUP)).post(
        "/api/v1/company-products/batch-lookup", json={"ids": [missing, first, first]}
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == [missing, first]  # orden de entrada, sin duplicados
    assert items[0]["found"] is False
    assert items[1]["found"] is True and "sale_price" not in items[1]  # spec 019
    assert GUARANTEED["product"] <= {k for k, v in items[1].items()}
    assert fake_oc.access_calls == []


def test_batch_lookup_human_checks_once_per_company(as_user, company, fake_catalog, fake_oc):
    client = as_user("consulta.test")
    admin = as_user("admin.test")
    other = uuid4()
    fake_oc.add_member(user_sub("admin.test"), other)
    mine = [adopt(admin, company, fake_catalog, internal_code=f"M{i}")["id"] for i in range(3)]
    foreign = adopt(admin, other, fake_catalog, internal_code="F")["id"]
    fake_oc.access_calls.clear()

    items = client.post("/api/v1/company-products/batch-lookup", json={"ids": [*mine, foreign]}).json()["items"]

    assert [item["found"] for item in items] == [True, True, True, False]
    assert sorted(company_id for _, company_id in fake_oc.access_calls) == sorted([company, other])


def test_batch_limits(as_token, service_token):
    client = as_token(service_token(READ["product"], LOOKUP))
    too_many = client.post("/api/v1/company-products/batch-lookup", json={"ids": [str(uuid4()) for _ in range(101)]})
    assert too_many.status_code == 422 and code_of(too_many) == "BATCH_LIMIT_EXCEEDED"

    same = str(uuid4())
    dedup = client.post("/api/v1/company-products/batch-lookup", json={"ids": [same] * 150})
    assert dedup.status_code == 200 and len(dedup.json()["items"]) == 1  # el límite se aplica tras quitar duplicados

    empty = client.post("/api/v1/company-products/batch-lookup", json={"ids": []})
    assert empty.status_code == 422 and code_of(empty) == "VALIDATION_ERROR"
