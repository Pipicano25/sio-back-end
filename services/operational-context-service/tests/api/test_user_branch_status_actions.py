"""Retiro y reactivación de asignaciones (US6; FR-023, RN-10, DS-11; RC-09)."""

import pytest


@pytest.fixture
def assignment(api, create_company, create_branch, fake_accounts, fake_persons):
    company = create_company()
    branch = create_branch(company["id"])
    user = api.post(
        f"/api/v1/companies/{company['id']}/application-users",
        json={
            "keycloak_user_id": fake_accounts.add("compras.test"),
            "person_identity_id": str(fake_persons.add()),
            "display_name": "C",
        },
    ).json()
    created = api.post(
        f"/api/v1/application-users/{user['id']}/user-branches", json={"branch_id": branch["id"]}
    ).json()
    return {"company": company, "branch": branch, "user": user, "created": created}


def test_deactivate_and_reactivate_manage_dates_and_author(api, api_as, assignment, make_member):
    url = f"/api/v1/user-branches/{assignment['created']['id']}"

    retired = api.post(f"{url}/deactivate", json={"version": 1}).json()
    assert retired["status"] == "INACTIVE" and retired["deactivated_at"] is not None

    make_member(assignment["company"]["id"], "supervisor.test")
    supervisor = api_as("perm:all:all:read", "perm:all:all:create", "perm:all:all:update", sub="supervisor.test")
    back = supervisor.post(f"{url}/reactivate", json={"version": 2}).json()

    assert back["status"] == "ACTIVE" and back["deactivated_at"] is None
    assert back["assigned_by"] == "supervisor.test"
    assert back["assigned_at"] > assignment["created"]["assigned_at"]


@pytest.mark.parametrize(
    ("inactivate", "code"),
    [("user", "MEMBERSHIP_INACTIVE"), ("branch", "BRANCH_INACTIVE"), ("company", "COMPANY_INACTIVE")],
)
def test_reactivate_rejected_under_inactive_parent(api, assignment, inactivate, code):
    url = f"/api/v1/user-branches/{assignment['created']['id']}"
    api.post(f"{url}/deactivate", json={"version": 1})
    target = {
        "user": f"/api/v1/application-users/{assignment['user']['id']}",
        "branch": f"/api/v1/branches/{assignment['branch']['id']}",
        "company": f"/api/v1/companies/{assignment['company']['id']}",
    }[inactivate]
    version = 1 if inactivate != "company" else assignment["company"]["version"]
    api.post(f"{target}/deactivate", json={"version": version})

    response = api.post(f"{url}/reactivate", json={"version": 2})

    assert response.status_code == 422
    assert response.json()["code"] == f"OPERATIONAL_CONTEXT.{code}"


@pytest.mark.parametrize("parent", ["branch", "company"])
def test_inactivating_parent_does_not_touch_assignments(api, assignment, parent):
    target = {
        "branch": f"/api/v1/branches/{assignment['branch']['id']}",
        "company": f"/api/v1/companies/{assignment['company']['id']}",
    }[parent]
    api.post(f"{target}/deactivate", json={"version": 1})

    reloaded = api.get(f"/api/v1/user-branches/{assignment['created']['id']}").json()

    assert reloaded["status"] == "ACTIVE" and reloaded["version"] == 1
    expected = "BRANCH_INACTIVE" if parent == "branch" else "COMPANY_INACTIVE"
    assert reloaded["operational_access"] == {"allowed": False, "reason": expected}


def test_repeated_transitions_and_stale_version(api, assignment):
    url = f"/api/v1/user-branches/{assignment['created']['id']}"

    assert api.post(f"{url}/reactivate", json={"version": 1}).status_code == 409
    assert api.post(f"{url}/deactivate", json={"version": 5}).json()["code"] == "OPERATIONAL_CONTEXT.VERSION_CONFLICT"
    api.post(f"{url}/deactivate", json={"version": 1})
    assert api.post(f"{url}/deactivate", json={"version": 2}).json()["code"] == (
        "OPERATIONAL_CONTEXT.INVALID_STATUS_TRANSITION"
    )
