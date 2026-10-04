"""Historia 3: clientes personas y organizaciones (FR-020 a FR-028; RC-06, RC-07, RC-13; DS-17)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from tests.api.helpers import code_of, organization_customer, person_customer
from tests.conftest import user_sub

URL = "/api/v1/companies/{company}/company-customers"


def _post(client, company, body):
    return client.post(URL.format(company=company), json=body)


def _put(client, customer, **overrides):
    body = {
        "internal_code": customer["internal_code"],
        "display_name": customer["display_name"],
        "preferred_contact_person_id": customer["preferred_contact_person_id"],
        "version": customer["version"],
        **overrides,
    }
    return client.put(f"/api/v1/company-customers/{customer['id']}", json=body)


def test_person_customer_stores_only_uuid(as_user, company, fake_party):
    customer = person_customer(as_user("supervisor.test"), company, fake_party)
    assert customer["customer_kind"] == "PERSON" and customer["status"] == "ACTIVE"
    assert customer["organization_identity_id"] is None
    assert customer["created_by"] == user_sub("supervisor.test")
    assert not {"first_name", "last_name", "email", "identification_number"} & set(customer)


def test_organization_customer_with_contact(as_user, company, fake_party):
    organization, contact = uuid4(), uuid4()
    fake_party.organizations[organization] = "ACTIVE"
    fake_party.add_contact(contact, organization)
    response = _post(
        as_user("admin.test"),
        company,
        {
            "customer_kind": "ORGANIZATION",
            "organization_identity_id": str(organization),
            "internal_code": "CLI-ORG",
            "display_name": "Organización",
            "preferred_contact_person_id": str(contact),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["preferred_contact_person_id"] == str(contact)
    assert not {"legal_name", "email", "phone"} & set(response.json())


@pytest.mark.parametrize("variant", ["other_org", "inactive", "missing"])
def test_invalid_contact(as_user, company, fake_party, variant):
    organization = uuid4()
    fake_party.organizations[organization] = "ACTIVE"
    contact = uuid4()
    if variant == "other_org":
        fake_party.add_contact(contact, uuid4())
    elif variant == "inactive":
        fake_party.add_contact(contact, organization, is_active=False)

    response = _post(
        as_user("admin.test"),
        company,
        {"customer_kind": "ORGANIZATION", "organization_identity_id": str(organization),
         "internal_code": "X", "display_name": "Y", "preferred_contact_person_id": str(contact)},
    )
    assert response.status_code == 422
    assert code_of(response) == "CONTACT_PERSON_INVALID"


def test_contact_not_allowed_for_person(as_user, company, fake_party):
    person = uuid4()
    fake_party.persons[person] = "ACTIVE"
    response = _post(
        as_user("admin.test"),
        company,
        {"customer_kind": "PERSON", "person_identity_id": str(person), "internal_code": "X",
         "display_name": "Y", "preferred_contact_person_id": str(uuid4())},
    )
    assert code_of(response) == "CONTACT_PERSON_NOT_ALLOWED"


@pytest.mark.parametrize(
    "body",
    [
        {"customer_kind": "PERSON"},
        {"customer_kind": "PERSON", "organization_identity_id": "ORG"},
        {"customer_kind": "PERSON", "person_identity_id": "P", "organization_identity_id": "ORG"},
        {"customer_kind": "ORGANIZATION", "person_identity_id": "P"},
    ],
)
def test_identity_mismatch(as_user, company, body):
    payload = {"internal_code": "X", "display_name": "Y", **body}
    for key in ("person_identity_id", "organization_identity_id"):
        if key in payload:
            payload[key] = str(uuid4())
    response = _post(as_user("admin.test"), company, payload)
    assert response.status_code == 422
    assert code_of(response) == "CUSTOMER_IDENTITY_MISMATCH"


def test_identity_not_found_and_inactive(as_user, company, fake_party):
    client = as_user("admin.test")
    missing = _post(client, company, {"customer_kind": "PERSON", "person_identity_id": str(uuid4()),
                                      "internal_code": "A", "display_name": "B"})
    assert code_of(missing) == "PERSON_IDENTITY_NOT_FOUND"

    person = uuid4()
    fake_party.persons[person] = "INACTIVE"
    inactive = _post(client, company, {"customer_kind": "PERSON", "person_identity_id": str(person),
                                       "internal_code": "A", "display_name": "B"})
    assert code_of(inactive) == "PERSON_IDENTITY_INACTIVE"

    organization = uuid4()
    fake_party.organizations[organization] = "INACTIVE"
    assert code_of(_post(client, company, {"customer_kind": "ORGANIZATION", "organization_identity_id": str(organization),
                                           "internal_code": "A", "display_name": "B"})) == "ORGANIZATION_IDENTITY_INACTIVE"
    assert code_of(_post(client, company, {"customer_kind": "ORGANIZATION", "organization_identity_id": str(uuid4()),
                                           "internal_code": "A", "display_name": "B"})) == "ORGANIZATION_IDENTITY_NOT_FOUND"


def test_duplicate_customer_in_any_state_and_duplicate_code(as_user, company, fake_party):
    client = as_user("admin.test")
    customer = person_customer(client, company, fake_party, internal_code="CLI-1")
    client.post(f"/api/v1/company-customers/{customer['id']}/deactivate", json={"version": 1})

    duplicate = _post(client, company, {"customer_kind": "PERSON", "person_identity_id": customer["person_identity_id"],
                                        "internal_code": "OTRO", "display_name": "x"})
    assert duplicate.status_code == 409 and code_of(duplicate) == "DUPLICATE_CUSTOMER"

    person = uuid4()
    fake_party.persons[person] = "ACTIVE"
    code = _post(client, company, {"customer_kind": "PERSON", "person_identity_id": str(person),
                                   "internal_code": "cli-1", "display_name": "x"})
    assert code.status_code == 409 and code_of(code) == "DUPLICATE_INTERNAL_CODE"


def test_self_relationship(as_user, company, fake_oc, fake_party):
    organization = fake_oc.organizations[company]
    fake_party.organizations[organization] = "ACTIVE"
    response = _post(as_user("admin.test"), company, {"customer_kind": "ORGANIZATION",
                                                      "organization_identity_id": str(organization),
                                                      "internal_code": "YO", "display_name": "Yo mismo"})
    assert response.status_code == 422
    assert code_of(response) == "SELF_RELATIONSHIP_NOT_ALLOWED"
    assert fake_party.calls == []


def test_person_does_not_query_company(as_user, company, fake_oc, fake_party):
    person_customer(as_user("admin.test"), company, fake_party)
    assert fake_oc.company_calls == []


def test_provider_failures(as_user, company, fake_oc, fake_party):
    client = as_user("admin.test")
    organization = uuid4()
    fake_party.organizations[organization] = "ACTIVE"
    body = {"customer_kind": "ORGANIZATION", "organization_identity_id": str(organization),
            "internal_code": "A", "display_name": "B"}

    fake_party.forbidden = True
    assert (r := _post(client, company, body)).status_code == 403 and code_of(r) == "PARTY_IDENTITY_ACCESS_DENIED"
    fake_party.forbidden = False

    fake_party.unavailable = True
    assert (r := _post(client, company, body)).status_code == 503 and r.json()["dependency"] == "party-identity"
    fake_party.unavailable = False

    fake_oc.company_forbidden = True
    assert (r := _post(client, company, body)).status_code == 403 and code_of(r) == "OPERATIONAL_ACCESS_DENIED"
    fake_oc.company_forbidden = False

    fake_oc.company_unavailable = True
    assert (r := _post(client, company, body)).status_code == 503 and r.json()["dependency"] == "operational-context"

    assert client.get(URL.format(company=company), params={"status": "ALL"}).json()["total_records"] == 0


def test_update_and_immutables(as_user, company, fake_party):
    client = as_user("admin.test")
    customer = organization_customer(client, company, fake_party)
    organization = customer["organization_identity_id"]
    contact = fake_party.add_contact(uuid4(), UUID(organization))

    response = _put(client, customer, display_name="Nuevo", preferred_contact_person_id=str(contact))
    assert response.status_code == 200
    updated = response.json()
    assert updated["display_name"] == "Nuevo" and updated["version"] == 2

    calls = len(fake_party.calls)
    removed = _put(client, updated, preferred_contact_person_id=None)
    assert removed.status_code == 200 and removed.json()["preferred_contact_person_id"] is None
    assert len(fake_party.calls) == calls  # quitar el contacto no consulta Party Identity

    for field in ("customer_kind", "person_identity_id", "organization_identity_id", "company_id", "status"):
        body = {"internal_code": "X", "display_name": "Y", "version": 3, field: "ORGANIZATION"}
        response = client.put(f"/api/v1/company-customers/{customer['id']}", json=body)
        assert code_of(response) == "IMMUTABLE_FIELD", field


def test_status_actions(as_user, company, fake_party):
    customer = person_customer(as_user("admin.test"), company, fake_party)

    assert as_user("supervisor.test").post(f"/api/v1/company-customers/{customer['id']}/deactivate",
                                           json={"version": 1}).status_code == 403
    inactive = as_user("admin.test").post(f"/api/v1/company-customers/{customer['id']}/deactivate", json={"version": 1})
    assert inactive.status_code == 200 and inactive.json()["status"] == "INACTIVE"

    fake_party.persons[UUID(customer["person_identity_id"])] = "INACTIVE"
    rejected = as_user("supervisor.test").post(f"/api/v1/company-customers/{customer['id']}/reactivate", json={"version": 2})
    assert code_of(rejected) == "PERSON_IDENTITY_INACTIVE"

    fake_party.persons[UUID(customer["person_identity_id"])] = "ACTIVE"
    reactivated = as_user("supervisor.test").post(f"/api/v1/company-customers/{customer['id']}/reactivate", json={"version": 2})
    assert reactivated.status_code == 200 and reactivated.json()["status"] == "ACTIVE"


def test_reactivation_keeps_inactive_contact(as_user, company, fake_party):
    client = as_user("admin.test")
    organization, contact = uuid4(), uuid4()
    fake_party.organizations[organization] = "ACTIVE"
    fake_party.add_contact(contact, organization)
    customer = _post(client, company, {"customer_kind": "ORGANIZATION", "organization_identity_id": str(organization),
                                       "internal_code": "O", "display_name": "O",
                                       "preferred_contact_person_id": str(contact)}).json()
    client.post(f"/api/v1/company-customers/{customer['id']}/deactivate", json={"version": 1})
    fake_party.add_contact(contact, organization, is_active=False)

    response = client.post(f"/api/v1/company-customers/{customer['id']}/reactivate", json={"version": 2})
    assert response.status_code == 200
    assert response.json()["preferred_contact_person_id"] == str(contact)


def test_list_filters_and_search(as_user, company, fake_party):
    client = as_user("admin.test")
    person = person_customer(client, company, fake_party, internal_code="P-1", display_name="Ana Ficticia")
    org = organization_customer(client, company, fake_party, internal_code="O-1", display_name="Bodega Ficticia")

    def ids(**params):
        return [item["id"] for item in client.get(URL.format(company=company), params=params).json()["items"]]

    assert ids() == [person["id"], org["id"]]
    assert ids(customer_kind="ORGANIZATION") == [org["id"]]
    assert ids(person_identity_id=person["person_identity_id"]) == [person["id"]]
    assert ids(organization_identity_id=org["organization_identity_id"]) == [org["id"]]
    assert ids(search="bodega") == [org["id"]]
    assert ids(search="p-1") == [person["id"]]


def test_put_on_inactive_customer_and_code_reuse(as_user, company, fake_party):
    """DS-17: PUT sobre INACTIVE no reactiva; flujo de reutilización del código."""
    client = as_user("admin.test")
    a = person_customer(client, company, fake_party, internal_code="CLI-100")
    inactive = client.post(f"/api/v1/company-customers/{a['id']}/deactivate", json={"version": 1}).json()

    person_b = uuid4()
    fake_party.persons[person_b] = "ACTIVE"
    body_b = {"customer_kind": "PERSON", "person_identity_id": str(person_b), "internal_code": "CLI-100", "display_name": "B"}
    assert code_of(_post(client, company, body_b)) == "DUPLICATE_INTERNAL_CODE"  # inactivar no libera

    other = person_customer(client, company, fake_party, internal_code="CLI-200")
    assert code_of(_put(client, inactive, internal_code="cli-200")) == "DUPLICATE_INTERNAL_CODE"
    assert code_of(client.put(f"/api/v1/company-customers/{a['id']}", json={"internal_code": "X", "display_name": "Y",
                                                                             "version": 2, "person_identity_id": other["person_identity_id"]})) == "IMMUTABLE_FIELD"

    changed = _put(client, inactive, internal_code="CLI-100-OLD")
    assert changed.status_code == 200
    assert changed.json()["status"] == "INACTIVE"
    assert _post(client, company, body_b).status_code == 201


def test_put_with_inactive_company(as_user, company, fake_party, fake_oc):
    customer = person_customer(as_user("admin.test"), company, fake_party)
    fake_oc.inactive_companies.add(company)
    assert code_of(_put(as_user("admin.test"), customer, display_name="x")) == "COMPANY_INACTIVE"
