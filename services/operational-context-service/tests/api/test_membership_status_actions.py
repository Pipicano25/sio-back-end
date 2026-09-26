"""Inactivación y reactivación de membresías (US6; FR-014, FR-044, R-14; RC-09, DS-11)."""

import pytest
from sqlalchemy import text

SUPERVISOR = ("perm:all:all:read", "perm:all:all:create", "perm:all:all:update")
READ = "perm:operational-context:application_users:read"


@pytest.fixture
def member(api, create_company, create_branch, fake_accounts, fake_persons):
    """Persona miembro de dos empresas, asignada a una sucursal de la primera."""
    sub = fake_accounts.add("compras.test")
    person = fake_persons.add()
    first, second = create_company(), create_company()
    branch = create_branch(first["id"])
    users = [
        api.post(
            f"/api/v1/companies/{company['id']}/application-users",
            json={"keycloak_user_id": sub, "person_identity_id": str(person), "display_name": "C"},
        ).json()
        for company in (first, second)
    ]
    assignment = api.post(
        f"/api/v1/application-users/{users[0]['id']}/user-branches", json={"branch_id": branch["id"]}
    ).json()
    fake_accounts.reset()
    fake_persons.reset()
    return {
        "sub": sub,
        "person": person,
        "first": first,
        "second": second,
        "branch": branch,
        "users": users,
        "assignment": assignment,
    }


def _access(api_as, member, **params):
    return api_as(READ, sub=member["sub"]).get("/api/v1/operational-access", params=params).json()


def test_deactivate_only_that_membership(api, api_as, member, fake_accounts, fake_persons):
    first_user, second_user = member["users"]

    response = api.post(f"/api/v1/application-users/{first_user['id']}/deactivate", json={"version": 1})

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE" and response.json()["version"] == 2
    assert api.get(f"/api/v1/application-users/{second_user['id']}").json()["status"] == "ACTIVE"
    assignment = api.get(f"/api/v1/user-branches/{member['assignment']['id']}").json()
    assert assignment["status"] == "ACTIVE" and assignment["version"] == 1
    assert assignment["operational_access"]["reason"] == "USER_MEMBERSHIP_INACTIVE"
    assert _access(api_as, member, branch_id=member["branch"]["id"])["reason"] == "USER_MEMBERSHIP_INACTIVE"
    assert _access(api_as, member, company_id=member["second"]["id"])["allowed"] is True
    assert fake_accounts.count() == 0 and fake_persons.count() == 0


def test_reactivate_revalidates_and_restores_assignments(api, api_as, member, fake_accounts, fake_persons):
    user = member["users"][0]
    api.post(f"/api/v1/application-users/{user['id']}/deactivate", json={"version": 1})

    response = api.post(f"/api/v1/application-users/{user['id']}/reactivate", json={"version": 2})

    assert response.status_code == 200 and response.json()["status"] == "ACTIVE"
    assert fake_accounts.count("get_account") == 1 and fake_persons.count("get_person") == 1
    assert _access(api_as, member, branch_id=member["branch"]["id"])["allowed"] is True


@pytest.mark.parametrize(
    ("setup", "status", "code"),
    [
        ("person_inactive", 422, "PERSON_IDENTITY_INACTIVE"),
        ("account_disabled", 422, "KEYCLOAK_USER_DISABLED"),
        ("keycloak_down", 503, "DEPENDENCY_UNAVAILABLE"),
        ("party_identity_down", 503, "DEPENDENCY_UNAVAILABLE"),
    ],
)
def test_reactivate_rejections(api, member, fake_accounts, fake_persons, setup, status, code):
    user = member["users"][0]
    api.post(f"/api/v1/application-users/{user['id']}/deactivate", json={"version": 1})

    if setup == "person_inactive":
        fake_persons.persons[member["person"]] = "INACTIVE"
    elif setup == "account_disabled":
        account = fake_accounts.accounts[member["sub"]]
        fake_accounts.accounts[member["sub"]] = type(account)(
            sub=account.sub, username=account.username, enabled=False, is_service_account=False
        )
    elif setup == "keycloak_down":
        fake_accounts.mode = "unavailable"
    else:
        fake_persons.mode = "unavailable"

    response = api.post(f"/api/v1/application-users/{user['id']}/reactivate", json={"version": 2})

    assert response.status_code == status
    assert response.json()["code"] == f"OPERATIONAL_CONTEXT.{code}"
    assert api.get(f"/api/v1/application-users/{user['id']}").json()["status"] == "INACTIVE"


def test_reactivate_with_another_active_membership_is_409(api, member, fake_accounts):
    user = member["users"][0]
    api.post(f"/api/v1/application-users/{user['id']}/deactivate", json={"version": 1})
    api.post(
        f"/api/v1/companies/{member['first']['id']}/application-users",
        json={"keycloak_user_id": member["sub"], "person_identity_id": str(member["person"]), "display_name": "N"},
    )

    response = api.post(f"/api/v1/application-users/{user['id']}/reactivate", json={"version": 2})

    assert response.status_code == 409
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.DUPLICATE_MEMBERSHIP"


def test_reactivate_under_inactive_company_is_422(api, member):
    user, company = member["users"][0], member["first"]
    api.post(f"/api/v1/application-users/{user['id']}/deactivate", json={"version": 1})
    api.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": company["version"]})

    response = api.post(f"/api/v1/application-users/{user['id']}/reactivate", json={"version": 2})

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.COMPANY_INACTIVE"


def test_repeated_transitions_and_stale_version(api, member):
    user = member["users"][0]
    url = f"/api/v1/application-users/{user['id']}"

    assert api.post(f"{url}/reactivate", json={"version": 1}).json()["code"] == (
        "OPERATIONAL_CONTEXT.INVALID_STATUS_TRANSITION"
    )
    assert api.post(f"{url}/deactivate", json={"version": 9}).json()["code"] == "OPERATIONAL_CONTEXT.VERSION_CONFLICT"
    api.post(f"{url}/deactivate", json={"version": 1})
    repeated = api.post(f"{url}/deactivate", json={"version": 2})
    assert repeated.status_code == 409
    assert api.get(url).json()["version"] == 2


def test_supervisor_cannot_deactivate(api_as, member, make_member):
    make_member(member["first"]["id"], "supervisor.test")
    supervisor = api_as(*SUPERVISOR, sub="supervisor.test")

    response = supervisor.post(
        f"/api/v1/application-users/{member['users'][0]['id']}/deactivate", json={"version": 1}
    )

    assert response.status_code == 403


def test_company_admin_deactivates_own_membership_and_loses_access(api_as, member, make_member, create_company):
    """C2: autoinactivación; con el mismo token la siguiente solicitud ya no ve la empresa."""
    company = member["first"]
    own_id = make_member(company["id"], "admin-empresa")
    company_admin = api_as(
        "perm:operational-context:companies:read",
        "perm:operational-context:application_users:read",
        "perm:operational-context:application_users:update",
        "perm:operational-context:application_users:delete",
        sub="admin-empresa",
    )

    assert company_admin.get(f"/api/v1/companies/{company['id']}").status_code == 200

    response = company_admin.post(f"/api/v1/application-users/{own_id}/deactivate", json={"version": 1})
    assert response.status_code == 200

    after = company_admin.get(f"/api/v1/companies/{company['id']}")
    access = company_admin.get("/api/v1/operational-access", params={"company_id": company["id"]})
    assert after.status_code == 404
    assert access.status_code == 200  # el token sigue siendo válido: no hay 401
    assert access.json()["reason"] == "USER_MEMBERSHIP_INACTIVE"


def test_no_physical_delete(api, member, test_engine):
    user = member["users"][0]
    api.post(f"/api/v1/application-users/{user['id']}/deactivate", json={"version": 1})

    assert api.delete(f"/api/v1/application-users/{user['id']}").status_code == 405
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM application_users")).scalar_one() == 2
