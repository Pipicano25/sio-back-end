"""Historia 8: resumen de las empresas del usuario (FR-046, DS-18; contracts/rest-api.md §4)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.helpers import adopt, code_of, organization_customer, person_customer, supplier
from tests.conftest import user_sub

URL = "/api/v1/company-summaries"
CR_READS = (
    "perm:commercial-relationship:company_products:read",
    "perm:commercial-relationship:company_customers:read",
    "perm:commercial-relationship:company_suppliers:read",
)


@pytest.fixture
def two_companies(as_user, company, other_company, fake_oc, fake_catalog, fake_party):
    """`admin.test` es miembro de `company` y de `other_company`, con datos distintos en cada una."""
    fake_oc.add_member(user_sub("admin.test"), other_company)
    fake_party.names[fake_oc.organizations[company]] = "DROGUERÍA A S.A.S."
    fake_party.names[fake_oc.organizations[other_company]] = "DISTRIBUIDORA B LTDA."
    admin = as_user("admin.test")

    first = adopt(admin, company, fake_catalog, internal_code="P-1")
    adopt(admin, company, fake_catalog, internal_code="P-2")
    admin.post(f"/api/v1/company-products/{first['id']}/deactivate", json={"version": first["version"]})
    person_customer(admin, company, fake_party)
    organization_customer(admin, company, fake_party)
    blocked = supplier(admin, company, fake_party)
    response = admin.post(
        f"/api/v1/company-suppliers/{blocked['id']}/block",
        json={"block_reason": "Prueba", "version": blocked["version"]},
    )
    assert response.status_code == 200, response.text

    adopt(admin, other_company, fake_catalog, internal_code="P-1")
    return {company: "DROGUERÍA A S.A.S.", other_company: "DISTRIBUIDORA B LTDA."}


def _all_pages(client, **params):
    items, page = [], 1
    while True:
        body = client.get(URL, params={**params, "page": page}).json()
        items.extend(body["items"])
        if page >= body["total_pages"]:
            return items, body
        page += 1


def test_default_is_one_company_per_page(as_user, two_companies):
    response = as_user("admin.test").get(URL)

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["page"], body["page_size"], body["total_records"], body["total_pages"]) == (1, 1, 2, 2)
    assert len(body["items"]) == 1


def test_pages_cover_member_companies_in_company_id_order(as_user, two_companies):
    items, _ = _all_pages(as_user("admin.test"))

    assert [item["company_id"] for item in items] == sorted(str(company) for company in two_companies)
    assert {item["company_id"]: item["legal_name"] for item in items} == {
        str(company): name for company, name in two_companies.items()
    }


def test_counts_by_status_are_isolated_per_company(as_user, company, other_company, two_companies):
    response = as_user("admin.test").get(URL, params={"page_size": 100})
    items = {item["company_id"]: item for item in response.json()["items"]}

    assert items[str(company)] == {
        "company_id": str(company),
        "company_status": "ACTIVE",
        "legal_name": "DROGUERÍA A S.A.S.",
        "company_products": {"total": 2, "ACTIVE": 1, "INACTIVE": 1},
        "company_customers": {"total": 2, "ACTIVE": 2, "INACTIVE": 0},
        "company_suppliers": {"total": 1, "ACTIVE": 0, "INACTIVE": 0, "BLOCKED": 1},
    }
    assert items[str(other_company)]["company_products"] == {"total": 1, "ACTIVE": 1, "INACTIVE": 0}
    assert items[str(other_company)]["company_customers"] == {"total": 0, "ACTIVE": 0, "INACTIVE": 0}
    assert items[str(other_company)]["company_suppliers"] == {"total": 0, "ACTIVE": 0, "INACTIVE": 0, "BLOCKED": 0}


def test_only_active_memberships_appear(as_user, company, other_company, fake_oc, two_companies):
    fake_oc.deactivate_member(user_sub("admin.test"), other_company)
    foreign = uuid4()  # empresa ajena con datos: nunca aparece
    fake_oc.organizations[foreign] = uuid4()
    fake_oc.add_member("sub-otro-usuario", foreign)

    items, body = _all_pages(as_user("admin.test"))

    assert body["total_records"] == 1
    assert [item["company_id"] for item in items] == [str(company)]


def test_supervisor_does_not_see_company_where_not_member(as_user, company, other_company, two_companies):
    items, body = _all_pages(as_user("supervisor.test"))

    assert body["total_records"] == 1
    assert [item["company_id"] for item in items] == [str(company)]


def test_inactive_company_is_listed_with_its_status(as_user, company, fake_oc, two_companies):
    fake_oc.inactive_companies.add(company)

    items, _ = _all_pages(as_user("admin.test"))

    assert {item["company_id"]: item["company_status"] for item in items}[str(company)] == "INACTIVE"


def test_no_memberships_is_empty_page(as_token, make_token):
    response = as_token(make_token(*CR_READS, sub="sub-sin-empresas")).get(URL)

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 1, "total_records": 0, "total_pages": 0}


def test_counts_are_null_without_their_read_permission(as_token, make_token, fake_oc, company, two_companies):
    token = make_token("perm:commercial-relationship:company_products:read", sub=user_sub("admin.test"))

    item = as_token(token).get(URL, params={"page_size": 100}).json()["items"]
    item = {entry["company_id"]: entry for entry in item}[str(company)]

    assert item["company_products"]["total"] == 2
    assert item["company_customers"] is None
    assert item["company_suppliers"] is None


def test_without_products_read_is_403_before_operational_context(as_token, make_token, fake_oc):
    token = make_token(CR_READS[1], CR_READS[2], sub=user_sub("admin.test"))

    response = as_token(token).get(URL)

    assert response.status_code == 403
    assert code_of(response) == "FORBIDDEN"
    assert fake_oc.me_calls == []


def test_without_token_is_401(as_token, fake_oc):
    response = as_token(None).get(URL)

    assert response.status_code == 401
    assert fake_oc.me_calls == []


@pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}, {"page": "x"}])
def test_invalid_pagination_is_422(as_user, company, params):
    response = as_user("admin.test").get(URL, params=params)

    assert response.status_code == 422
    assert code_of(response) == "VALIDATION_ERROR"


def test_page_size_100_is_allowed(as_user, two_companies):
    response = as_user("admin.test").get(URL, params={"page_size": 100})

    assert response.status_code == 200
    assert len(response.json()["items"]) == 2


def test_page_beyond_last_is_empty(as_user, two_companies):
    body = as_user("admin.test").get(URL, params={"page": 5}).json()

    assert body["items"] == []
    assert body["total_records"] == 2


def test_legal_name_is_null_when_company_or_organization_is_not_visible(as_user, company, fake_oc, fake_party, two_companies):
    fake_party.forbidden = True
    items, _ = _all_pages(as_user("admin.test"))
    assert all(item["legal_name"] is None for item in items)

    fake_party.forbidden = False
    fake_oc.company_forbidden = True
    items, _ = _all_pages(as_user("admin.test"))
    assert all(item["legal_name"] is None for item in items)

    fake_oc.company_forbidden = False
    del fake_party.names[fake_oc.organizations[company]]
    items, _ = _all_pages(as_user("admin.test"))
    assert {item["company_id"]: item["legal_name"] for item in items}[str(company)] is None


def test_operational_context_denied_is_403(as_user, company, fake_oc):
    fake_oc.access_forbidden = True

    response = as_user("admin.test").get(URL)

    assert response.status_code == 403
    assert code_of(response) == "OPERATIONAL_ACCESS_DENIED"


def test_operational_context_unavailable_is_503(as_user, company, fake_oc):
    fake_oc.access_unavailable = True

    response = as_user("admin.test").get(URL)

    assert response.status_code == 503
    assert code_of(response) == "DEPENDENCY_UNAVAILABLE"
    assert response.json()["dependency"] == "operational-context"


def test_company_lookup_unavailable_is_503(as_user, company, fake_oc):
    fake_oc.company_unavailable = True

    response = as_user("admin.test").get(URL)

    assert response.status_code == 503
    assert response.json()["dependency"] == "operational-context"


def test_party_identity_unavailable_is_503(as_user, company, fake_party):
    fake_party.unavailable = True

    response = as_user("admin.test").get(URL)

    assert response.status_code == 503
    assert response.json()["dependency"] == "party-identity"


def test_names_are_looked_up_only_for_the_page(as_user, company, other_company, fake_oc, fake_party, two_companies):
    fake_oc.company_calls.clear()
    fake_party.calls.clear()

    as_user("admin.test").get(URL)

    assert len(fake_oc.company_calls) == 1
    assert [call[0] for call in fake_party.calls] == ["get_organization_name"]


def test_technical_identity_with_lookup_gets_no_platform_scope(as_token, service_token, company, two_companies):
    token = service_token(*CR_READS, "perm:commercial-relationship:platform:lookup")

    response = as_token(token).get(URL)

    assert response.status_code == 200
    assert response.json()["total_records"] == 0


def test_summary_does_not_modify_data(as_user, company, two_companies):
    admin = as_user("admin.test")
    before = admin.get(f"/api/v1/companies/{company}/company-products", params={"status": "ALL"}).json()

    admin.get(URL, params={"page_size": 100})

    after = admin.get(f"/api/v1/companies/{company}/company-products", params={"status": "ALL"}).json()
    assert before == after
