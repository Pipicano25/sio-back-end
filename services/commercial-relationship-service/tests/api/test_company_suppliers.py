"""Historia 4: proveedores, bloqueo y desbloqueo (FR-030 a FR-035; DS-10, DS-16, DS-17)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from tests.api.helpers import code_of, organization_customer, supplier

URL = "/api/v1/companies/{company}/company-suppliers"


def _action(client, item, action, **body):
    return client.post(
        f"/api/v1/company-suppliers/{item['id']}/{action}", json={"version": item["version"], **body}
    )


def _put(client, item, **overrides):
    body = {
        "internal_code": item["internal_code"],
        "display_name": item["display_name"],
        "preferred_contact_person_id": item["preferred_contact_person_id"],
        "version": item["version"],
        **overrides,
    }
    return client.put(f"/api/v1/company-suppliers/{item['id']}", json=body)


def test_select_supplier(as_user, company, fake_party):
    created = supplier(as_user("supervisor.test"), company, fake_party)
    assert created["status"] == "ACTIVE" and created["block_reason"] is None
    assert not {"legal_name", "email"} & set(created)


def test_duplicate_supplier_and_same_org_as_customer(as_user, company, fake_party):
    client = as_user("admin.test")
    customer = organization_customer(client, company, fake_party)
    as_supplier = supplier(client, company, fake_party, organization_identity_id=customer["organization_identity_id"])
    assert as_supplier["organization_identity_id"] == customer["organization_identity_id"]

    _action(client, as_supplier, "deactivate")
    response = client.post(
        URL.format(company=company),
        json={"organization_identity_id": as_supplier["organization_identity_id"], "internal_code": "Z", "display_name": "Z"},
    )
    assert response.status_code == 409 and code_of(response) == "DUPLICATE_SUPPLIER"


def test_block_requires_delete_and_reason(as_user, company, fake_party):
    created = supplier(as_user("admin.test"), company, fake_party)

    assert _action(as_user("supervisor.test"), created, "block", block_reason="Incumplimiento").status_code == 403

    missing = _action(as_user("admin.test"), created, "block")
    assert missing.status_code == 422 and code_of(missing) == "VALIDATION_ERROR"
    too_long = _action(as_user("admin.test"), created, "block", block_reason="x" * 501)
    assert too_long.status_code == 422
    blank = _action(as_user("admin.test"), created, "block", block_reason="   ")
    assert blank.status_code == 422

    blocked = _action(as_user("admin.test"), created, "block", block_reason="  Incumplimiento de entregas  ")
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "BLOCKED"
    assert blocked.json()["block_reason"] == "Incumplimiento de entregas"


def test_blocked_transitions(as_user, company, fake_party):
    client = as_user("admin.test")
    created = supplier(client, company, fake_party)
    blocked = _action(client, created, "block", block_reason="Revisión").json()

    for action in ("reactivate", "deactivate"):
        response = _action(client, blocked, action)
        assert response.status_code == 409 and code_of(response) == "INVALID_STATUS_TRANSITION", action
    again = _action(client, blocked, "block", block_reason="otra")
    assert again.status_code == 409

    unblocked = _action(as_user("supervisor.test"), blocked, "unblock")
    assert unblocked.status_code == 200
    assert unblocked.json()["status"] == "ACTIVE" and unblocked.json()["block_reason"] is None


def test_block_from_inactive_and_unblock_with_inactive_org(as_user, company, fake_party):
    client = as_user("admin.test")
    created = supplier(client, company, fake_party)
    inactive = _action(client, created, "deactivate").json()
    blocked = _action(client, inactive, "block", block_reason="Motivo").json()
    assert blocked["status"] == "BLOCKED"

    fake_party.organizations[UUID(created["organization_identity_id"])] = "INACTIVE"
    response = _action(client, blocked, "unblock")
    assert code_of(response) == "ORGANIZATION_IDENTITY_INACTIVE"


def test_self_relationship(as_user, company, fake_oc, fake_party):
    own = fake_oc.organizations[company]
    fake_party.organizations[own] = "ACTIVE"
    response = as_user("admin.test").post(
        URL.format(company=company), json={"organization_identity_id": str(own), "internal_code": "Y", "display_name": "Y"}
    )
    assert response.status_code == 422 and code_of(response) == "SELF_RELATIONSHIP_NOT_ALLOWED"


def test_contact_of_other_organization(as_user, company, fake_party):
    organization = uuid4()
    fake_party.organizations[organization] = "ACTIVE"
    contact = fake_party.add_contact(uuid4(), uuid4())
    response = as_user("admin.test").post(
        URL.format(company=company),
        json={"organization_identity_id": str(organization), "internal_code": "C", "display_name": "C",
              "preferred_contact_person_id": str(contact)},
    )
    assert code_of(response) == "CONTACT_PERSON_INVALID"


@pytest.mark.parametrize("field", ["status", "block_reason", "organization_identity_id", "company_id"])
def test_put_immutables(as_user, company, fake_party, field):
    created = supplier(as_user("admin.test"), company, fake_party)
    body = {"internal_code": "A", "display_name": "B", "version": 1, field: "x"}
    response = as_user("admin.test").put(f"/api/v1/company-suppliers/{created['id']}", json=body)
    assert code_of(response) == "IMMUTABLE_FIELD"


def test_put_on_blocked_and_inactive_keeps_state(as_user, company, fake_party):
    """DS-17: PUT sobre BLOCKED no desbloquea; sobre INACTIVE no reactiva."""
    client = as_user("admin.test")
    created = supplier(client, company, fake_party, internal_code="PRV-1")
    blocked = _action(client, created, "block", block_reason="Motivo").json()

    response = _put(client, blocked, display_name="Corregido")
    assert response.status_code == 200
    assert response.json()["status"] == "BLOCKED" and response.json()["block_reason"] == "Motivo"

    other = supplier(client, company, fake_party, internal_code="PRV-2")
    assert code_of(_put(client, response.json(), internal_code="prv-2")) == "DUPLICATE_INTERNAL_CODE"

    inactive = _action(client, other, "deactivate").json()
    edited = _put(client, inactive, display_name="Inactivo editado")
    assert edited.status_code == 200 and edited.json()["status"] == "INACTIVE"


def test_code_reuse_after_changing_inactive_supplier(as_user, company, fake_party):
    client = as_user("admin.test")
    old = supplier(client, company, fake_party, internal_code="PRV-9")
    inactive = _action(client, old, "deactivate").json()

    new_org = uuid4()
    fake_party.organizations[new_org] = "ACTIVE"
    body = {"organization_identity_id": str(new_org), "internal_code": "PRV-9", "display_name": "Nuevo"}
    assert code_of(client.post(URL.format(company=company), json=body)) == "DUPLICATE_INTERNAL_CODE"

    assert _put(client, inactive, internal_code="PRV-9-OLD").status_code == 200
    assert client.post(URL.format(company=company), json=body).status_code == 201


def test_inactive_company_rules(as_user, company, fake_party, fake_oc):
    client = as_user("admin.test")
    active = supplier(client, company, fake_party, internal_code="A")
    blocked = _action(client, supplier(client, company, fake_party, internal_code="B"), "block", block_reason="M").json()
    inactive = _action(client, supplier(client, company, fake_party, internal_code="C"), "deactivate").json()
    fake_oc.inactive_companies.add(company)

    assert code_of(_action(client, active, "block", block_reason="M")) == "COMPANY_INACTIVE"
    assert code_of(_action(client, blocked, "unblock")) == "COMPANY_INACTIVE"
    assert code_of(_action(client, inactive, "reactivate")) == "COMPANY_INACTIVE"
    for item in (active, blocked, inactive):
        assert code_of(_put(client, item, display_name="x")) == "COMPANY_INACTIVE"
    assert _action(client, active, "deactivate").status_code == 200


def test_list_blocked(as_user, company, fake_party):
    client = as_user("admin.test")
    created = supplier(client, company, fake_party)
    _action(client, created, "block", block_reason="M")
    listing = client.get(URL.format(company=company), params={"status": "BLOCKED"}).json()
    assert [item["id"] for item in listing["items"]] == [created["id"]]
    assert client.get(URL.format(company=company)).json()["total_records"] == 0
