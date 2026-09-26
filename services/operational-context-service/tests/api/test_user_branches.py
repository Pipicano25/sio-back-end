"""Asignaciones usuario–sucursal (US2; FR-020 a FR-025; RC-06, RC-12)."""

import pytest


@pytest.fixture
def setup(api, create_company, create_branch, fake_accounts, fake_persons):
    """Empresa con dos sucursales y un usuario operativo; otra empresa con una sucursal."""
    company = create_company()
    other = create_company()
    branch = create_branch(company["id"], code="S-1")
    second = create_branch(company["id"], code="S-2")
    foreign_branch = create_branch(other["id"], code="X-1")
    sub = fake_accounts.add("compras.test")
    user = api.post(
        f"/api/v1/companies/{company['id']}/application-users",
        json={"keycloak_user_id": sub, "person_identity_id": str(fake_persons.add()), "display_name": "C"},
    ).json()
    fake_accounts.reset()
    fake_persons.reset()
    return {
        "company": company,
        "branch": branch,
        "second": second,
        "foreign_branch": foreign_branch,
        "user": user,
    }


def _assign(client, user_id, branch_id):
    return client.post(f"/api/v1/application-users/{user_id}/user-branches", json={"branch_id": branch_id})


def test_assign_branch_of_same_company(api, setup, fake_accounts, fake_persons):
    response = _assign(api, setup["user"]["id"], setup["branch"]["id"])

    assert response.status_code == 201, response.text
    body = response.json()
    assert response.headers["Location"] == f"/api/v1/user-branches/{body['id']}"
    assert body["status"] == "ACTIVE"
    assert body["assigned_by"] == "user-admin"
    assert body["deactivated_at"] is None
    assert body["company_id"] == setup["company"]["id"]
    assert body["membership_status"] == body["branch_status"] == body["company_status"] == "ACTIVE"
    assert body["operational_access"] == {"allowed": True, "reason": None}
    assert fake_accounts.count() == 0 and fake_persons.count() == 0


def test_branch_of_another_company_is_422(api, setup):
    response = _assign(api, setup["user"]["id"], setup["foreign_branch"]["id"])

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.BRANCH_COMPANY_MISMATCH"


def test_duplicate_pair_including_inactive_is_409(api, setup):
    created = _assign(api, setup["user"]["id"], setup["branch"]["id"]).json()
    api.post(f"/api/v1/user-branches/{created['id']}/deactivate", json={"version": 1})

    response = _assign(api, setup["user"]["id"], setup["branch"]["id"])

    assert response.status_code == 409
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.DUPLICATE_USER_BRANCH"


def test_inactive_membership_branch_or_company_is_422(api, setup):
    user, branch, second = setup["user"], setup["branch"], setup["second"]

    api.post(f"/api/v1/branches/{second['id']}/deactivate", json={"version": 1})
    assert _assign(api, user["id"], second["id"]).json()["code"] == "OPERATIONAL_CONTEXT.BRANCH_INACTIVE"

    api.post(f"/api/v1/application-users/{user['id']}/deactivate", json={"version": 1})
    assert _assign(api, user["id"], branch["id"]).json()["code"] == "OPERATIONAL_CONTEXT.MEMBERSHIP_INACTIVE"


def test_inactive_company_is_422(api, setup):
    company = setup["company"]
    api.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": company["version"]})

    response = _assign(api, setup["user"]["id"], setup["branch"]["id"])

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.COMPANY_INACTIVE"


@pytest.mark.parametrize("extra", [{"assigned_by": "otro"}, {"company_id": "x"}, {"status": "INACTIVE"}])
def test_body_cannot_set_managed_fields(api, setup, extra):
    response = api.post(
        f"/api/v1/application-users/{setup['user']['id']}/user-branches",
        json={"branch_id": setup["branch"]["id"], **extra},
    )

    assert response.status_code == 422


def test_collections_by_user_and_by_branch(api, setup):
    user = setup["user"]
    first = _assign(api, user["id"], setup["branch"]["id"]).json()
    second = _assign(api, user["id"], setup["second"]["id"]).json()
    api.post(f"/api/v1/user-branches/{second['id']}/deactivate", json={"version": 1})

    by_user = api.get(f"/api/v1/application-users/{user['id']}/user-branches").json()
    inactive = api.get(
        f"/api/v1/application-users/{user['id']}/user-branches", params={"status": "INACTIVE"}
    ).json()
    by_branch = api.get(f"/api/v1/branches/{setup['branch']['id']}/user-branches").json()

    assert [item["id"] for item in by_user["items"]] == [first["id"]]
    assert [item["id"] for item in inactive["items"]] == [second["id"]]
    assert [item["id"] for item in by_branch["items"]] == [first["id"]]
    assert api.get(f"/api/v1/user-branches/{second['id']}").json()["status"] == "INACTIVE"


def test_unknown_user_or_branch_is_404(api, setup):
    unknown = "00000000-0000-4000-8000-000000000999"

    assert _assign(api, unknown, setup["branch"]["id"]).status_code == 404
    assert _assign(api, setup["user"]["id"], unknown).status_code == 404
    assert api.get(f"/api/v1/user-branches/{unknown}").status_code == 404


def test_member_of_another_company_does_not_see_assignments(api, api_as, setup, make_member, create_company):
    created = _assign(api, setup["user"]["id"], setup["branch"]["id"]).json()
    outsider_company = create_company()
    make_member(outsider_company["id"], "ajeno")
    outsider = api_as("perm:operational-context:all:read", "perm:operational-context:user_branches:create", sub="ajeno")

    assert outsider.get(f"/api/v1/user-branches/{created['id']}").status_code == 404
    assert outsider.get(f"/api/v1/application-users/{setup['user']['id']}/user-branches").status_code == 404
    assert _assign(outsider, setup["user"]["id"], setup["second"]["id"]).status_code == 404


def test_company_member_can_assign_in_own_company(api_as, setup, make_member):
    make_member(setup["company"]["id"], "supervisor.test")
    supervisor = api_as("perm:all:all:read", "perm:all:all:create", "perm:all:all:update", sub="supervisor.test")

    response = _assign(supervisor, setup["user"]["id"], setup["branch"]["id"])

    assert response.status_code == 201
    assert response.json()["assigned_by"] == "supervisor.test"
