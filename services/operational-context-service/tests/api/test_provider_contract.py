"""Contrato Provider de empresa y sucursal por UUID (US1; FR-050 a FR-052, RC-07, SC-005).

Contrato: `specs/004-operational-context-core/contracts/operational-context-provider.md`.
"""

import pytest

from tests.conftest import random_uuid

COMPANY_GUARANTEED = {
    "id": str,
    "organization_identity_id": str,
    "status": str,
    "timezone": str,
    "default_currency": str,
    "version": int,
}
BRANCH_GUARANTEED = {
    "id": str,
    "company_id": str,
    "company_status": str,
    "status": str,
    "code": str,
    "name": str,
    "effective_timezone": str,
    "version": int,
}

# Consumidor técnico (Fase B, FR-045): lectura del recurso + `platform:lookup`,
# que permite consultar por UUID sin membresía.
LOOKUP = "perm:operational-context:platform:lookup"
READ_COMPANIES = "perm:operational-context:companies:read"
READ_BRANCHES = "perm:operational-context:branches:read"


def _assert_guaranteed(body, fields):
    for field, kind in fields.items():
        assert isinstance(body[field], kind), field


def test_company_active_and_inactive(api_as, api, create_company):
    consumer = api_as(READ_COMPANIES, LOOKUP)
    active = create_company()
    inactive = create_company()
    api.post(f"/api/v1/companies/{inactive['id']}/deactivate", json={"version": 1})

    active_response = consumer.get(f"/api/v1/companies/{active['id']}")
    inactive_response = consumer.get(f"/api/v1/companies/{inactive['id']}")

    assert active_response.status_code == 200 and active_response.json()["status"] == "ACTIVE"
    assert inactive_response.status_code == 200 and inactive_response.json()["status"] == "INACTIVE"
    _assert_guaranteed(active_response.json(), COMPANY_GUARANTEED)
    assert "x-trace-id" in active_response.headers


def test_branch_active_inactive_and_of_inactive_company(api_as, api, create_company, create_branch):
    consumer = api_as(READ_BRANCHES, LOOKUP)
    company = create_company()
    available = create_branch(company["id"], code="A")
    closed = create_branch(company["id"], code="B")
    api.post(f"/api/v1/branches/{closed['id']}/deactivate", json={"version": 1})

    body = consumer.get(f"/api/v1/branches/{available['id']}").json()
    assert body["status"] == "ACTIVE" and body["company_status"] == "ACTIVE"
    assert body["company_id"] == company["id"]
    _assert_guaranteed(body, BRANCH_GUARANTEED)
    assert consumer.get(f"/api/v1/branches/{closed['id']}").json()["status"] == "INACTIVE"

    api.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": 1})
    of_inactive_company = consumer.get(f"/api/v1/branches/{available['id']}").json()

    assert of_inactive_company["status"] == "ACTIVE"
    assert of_inactive_company["company_status"] == "INACTIVE"


@pytest.mark.parametrize("resource, permission", [("companies", READ_COMPANIES), ("branches", READ_BRANCHES)])
def test_not_found_malformed_unauthenticated_forbidden(api_as, anonymous, resource, permission):
    consumer = api_as(permission, LOOKUP)

    not_found = consumer.get(f"/api/v1/{resource}/{random_uuid()}")
    malformed = consumer.get(f"/api/v1/{resource}/no-es-uuid")

    assert not_found.status_code == 404
    assert not_found.json()["code"] == "OPERATIONAL_CONTEXT.NOT_FOUND"
    assert malformed.status_code == 422
    assert malformed.json()["code"] == "OPERATIONAL_CONTEXT.VALIDATION_ERROR"
    assert anonymous.get(f"/api/v1/{resource}/{random_uuid()}").status_code == 401
    assert api_as("perm:party-identity:all:read").get(f"/api/v1/{resource}/{random_uuid()}").status_code == 403


def test_consumer_distinguishes_states_with_one_call(api_as, api, create_company, create_branch):
    """SC-005: disponible, inactiva (o de empresa inactiva), inexistente y sin permiso."""
    consumer = api_as(READ_BRANCHES, LOOKUP)
    company = create_company()
    branch = create_branch(company["id"])

    def availability(branch_id):
        response = consumer.get(f"/api/v1/branches/{branch_id}")
        if response.status_code != 200:
            return response.status_code
        body = response.json()
        return "disponible" if body["status"] == body["company_status"] == "ACTIVE" else "no-disponible"

    assert availability(branch["id"]) == "disponible"
    api.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": 1})
    assert availability(branch["id"]) == "no-disponible"
    assert availability(random_uuid()) == 404
    assert api_as().get(f"/api/v1/branches/{branch['id']}").status_code == 403


# --------------------------------------------------------------------------
# Fase B: aislamiento en el contrato Provider (C-10, FR-041, FR-045, FR-073)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("resource, permission", [("companies", READ_COMPANIES), ("branches", READ_BRANCHES)])
def test_reader_without_membership_gets_404_like_unknown(api_as, create_company, create_branch, resource, permission):
    company = create_company()
    target = company if resource == "companies" else create_branch(company["id"])
    reader = api_as(permission)

    foreign = reader.get(f"/api/v1/{resource}/{target['id']}")
    unknown = reader.get(f"/api/v1/{resource}/{random_uuid()}")

    assert foreign.status_code == unknown.status_code == 404
    assert foreign.json()["code"] == unknown.json()["code"] == "OPERATIONAL_CONTEXT.NOT_FOUND"
    assert foreign.json()["detail"] == unknown.json()["detail"]


@pytest.mark.parametrize("resource, permission", [("companies", READ_COMPANIES), ("branches", READ_BRANCHES)])
def test_member_reads_without_lookup(api_as, create_company, create_branch, make_member, resource, permission):
    company = create_company()
    target = company if resource == "companies" else create_branch(company["id"])
    make_member(company["id"], "miembro")

    response = api_as(permission, sub="miembro").get(f"/api/v1/{resource}/{target['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == target["id"]


def test_lookup_does_not_allow_writes(api_as, create_company):
    company = create_company()
    technical = api_as("perm:operational-context:companies:update", LOOKUP)

    response = technical.put(
        f"/api/v1/companies/{company['id']}",
        json={
            "organization_identity_id": company["organization_identity_id"],
            "timezone": "America/Bogota",
            "default_currency": "COP",
            "version": 1,
        },
    )

    assert response.status_code == 404


def test_application_user_by_uuid_for_technical_consumer(api, api_as, create_company, fake_accounts, fake_persons):
    """FR-072: usuario operativo por UUID, en cualquier estado, con `platform:lookup`."""
    company = create_company()
    user = api.post(
        f"/api/v1/companies/{company['id']}/application-users",
        json={
            "keycloak_user_id": fake_accounts.add("compras.test"),
            "person_identity_id": str(fake_persons.add()),
            "display_name": "Compras",
        },
    ).json()
    api.post(f"/api/v1/application-users/{user['id']}/deactivate", json={"version": 1})
    consumer = api_as("perm:operational-context:application_users:read", LOOKUP)

    body = consumer.get(f"/api/v1/application-users/{user['id']}").json()

    for field, kind in {
        "id": str,
        "company_id": str,
        "keycloak_user_id": str,
        "person_identity_id": str,
        "display_name": str,
        "status": str,
        "version": int,
    }.items():
        assert isinstance(body[field], kind), field
    assert body["status"] == "INACTIVE"
    assert api_as("perm:operational-context:application_users:read").get(
        f"/api/v1/application-users/{user['id']}"
    ).status_code == 404
