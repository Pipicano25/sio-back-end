"""Inactivación y reactivación sin eliminar (US6; FR-017, FR-026, RC-08, RC-09, DS-07, DS-11, SC-007).

Prueba obligatoria 8 (reactivación bajo empresa inactiva).
"""

import pytest
from sqlalchemy import text

SUPERVISOR = ("perm:all:all:read", "perm:all:all:create", "perm:all:all:update")


def test_deactivate_company_keeps_row_and_does_not_touch_branches(api_as, api, create_company, create_branch, test_engine):
    company = create_company()
    branch = create_branch(company["id"])
    admin = api_as("perm:operational-context:companies:delete", sub="admin-2")

    response = admin.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "INACTIVE" and body["version"] == 2 and body["updated_by"] == "admin-2"
    assert api.get(f"/api/v1/companies/{company['id']}").status_code == 200

    reloaded = api.get(f"/api/v1/branches/{branch['id']}").json()
    assert reloaded["status"] == "ACTIVE"
    assert reloaded["version"] == branch["version"]
    assert reloaded["company_status"] == "INACTIVE"

    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM companies")).scalar_one() == 1


def test_reactivate_company(api, create_company):
    company = create_company()
    api.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": 1})

    response = api.post(f"/api/v1/companies/{company['id']}/reactivate", json={"version": 2})

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE" and response.json()["version"] == 3


@pytest.mark.parametrize("resource", ["companies", "branches"])
def test_repeated_transition_is_409_without_version_change(api, create_company, create_branch, resource):
    company = create_company()
    target = company if resource == "companies" else create_branch(company["id"])
    url = f"/api/v1/{resource}/{target['id']}"

    repeated = api.post(f"{url}/reactivate", json={"version": 1})

    assert repeated.status_code == 409
    assert repeated.json()["code"] == "OPERATIONAL_CONTEXT.INVALID_STATUS_TRANSITION"
    assert api.get(url).json()["version"] == 1

    api.post(f"{url}/deactivate", json={"version": 1})
    again = api.post(f"{url}/deactivate", json={"version": 2})

    assert again.status_code == 409
    assert api.get(url).json()["version"] == 2


@pytest.mark.parametrize("resource", ["companies", "branches"])
def test_stale_version_is_409(api, create_company, create_branch, resource):
    company = create_company()
    target = company if resource == "companies" else create_branch(company["id"])

    response = api.post(f"/api/v1/{resource}/{target['id']}/deactivate", json={"version": 7})

    assert response.status_code == 409
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.VERSION_CONFLICT"


@pytest.mark.parametrize("resource", ["companies", "branches"])
def test_supervisor_cannot_deactivate_but_can_reactivate(api_as, api, create_company, create_branch, resource):
    company = create_company()
    target = company if resource == "companies" else create_branch(company["id"])
    supervisor = api_as(*SUPERVISOR, sub="supervisor.test")
    url = f"/api/v1/{resource}/{target['id']}"

    assert supervisor.post(f"{url}/deactivate", json={"version": 1}).status_code == 403
    api.post(f"{url}/deactivate", json={"version": 1})
    assert supervisor.post(f"{url}/reactivate", json={"version": 2}).status_code == 200


def test_branch_deactivate_and_reactivate(api, create_company, create_branch):
    branch = create_branch(create_company()["id"])

    deactivated = api.post(f"/api/v1/branches/{branch['id']}/deactivate", json={"version": 1})
    reactivated = api.post(f"/api/v1/branches/{branch['id']}/reactivate", json={"version": 2})

    assert deactivated.json()["status"] == "INACTIVE"
    assert reactivated.json()["status"] == "ACTIVE" and reactivated.json()["version"] == 3


def test_reactivate_branch_of_inactive_company_is_422(api, create_company, create_branch):
    """Prueba obligatoria 8 (reactivación)."""
    company = create_company()
    branch = create_branch(company["id"])
    api.post(f"/api/v1/branches/{branch['id']}/deactivate", json={"version": 1})
    api.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": 1})

    response = api.post(f"/api/v1/branches/{branch['id']}/reactivate", json={"version": 2})

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.COMPANY_INACTIVE"
    assert api.get(f"/api/v1/branches/{branch['id']}").json()["status"] == "INACTIVE"


def test_collections_hide_inactive_by_default(api, create_company, create_branch):
    company = create_company()
    branch = create_branch(company["id"])
    api.post(f"/api/v1/branches/{branch['id']}/deactivate", json={"version": 1})
    url = f"/api/v1/companies/{company['id']}/branches"

    assert api.get(url).json()["total_records"] == 0
    assert api.get(url, params={"status": "INACTIVE"}).json()["total_records"] == 1


def test_status_actions_do_not_call_providers(api, create_company, create_branch, fake_organizations, fake_geography, geo):
    company = create_company(**geo.medellin_location())
    branch = create_branch(company["id"], **geo.medellin_location())
    fake_organizations.reset()
    fake_geography.reset()
    fake_organizations.mode = fake_geography.mode = "unavailable"

    api.post(f"/api/v1/branches/{branch['id']}/deactivate", json={"version": 1})
    api.post(f"/api/v1/branches/{branch['id']}/reactivate", json={"version": 2})
    api.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": 1})
    response = api.post(f"/api/v1/companies/{company['id']}/reactivate", json={"version": 2})

    assert response.status_code == 200
    assert fake_organizations.count() == 0 and fake_geography.count() == 0


@pytest.mark.parametrize("path", ["/api/v1/companies/{id}", "/api/v1/branches/{id}"])
def test_no_physical_delete_route(api, create_company, create_branch, path):
    """SC-007, RC-08."""
    company = create_company()
    branch = create_branch(company["id"])
    target = company["id"] if "companies" in path else branch["id"]

    response = api.delete(path.format(id=target))

    assert response.status_code == 405
    assert api.get(path.format(id=target)).status_code == 200
