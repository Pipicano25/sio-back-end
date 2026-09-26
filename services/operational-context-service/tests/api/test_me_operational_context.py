"""Contexto operativo propio (US4; FR-070)."""

READ = "perm:operational-context:application_users:read"
URL = "/api/v1/me/operational-context"


def test_without_memberships_is_empty(api_as):
    response = api_as(READ, sub="sin-empresas").get(URL)

    assert response.status_code == 200
    assert response.json() == {"keycloak_user_id": "sin-empresas", "memberships": []}


def test_memberships_in_two_companies_with_branch_access(
    api, api_as, create_company, create_branch, fake_accounts, fake_persons
):
    sub = fake_accounts.add("compras.test")
    person = str(fake_persons.add())
    first, second = create_company(), create_company()
    branch_ok = create_branch(first["id"], code="OK")
    branch_closed = create_branch(first["id"], code="CERRADA")
    memberships = {}
    for company in (first, second):
        memberships[company["id"]] = api.post(
            f"/api/v1/companies/{company['id']}/application-users",
            json={"keycloak_user_id": sub, "person_identity_id": person, "display_name": "C"},
        ).json()
    user = memberships[first["id"]]
    for branch in (branch_ok, branch_closed):
        api.post(f"/api/v1/application-users/{user['id']}/user-branches", json={"branch_id": branch["id"]})
    api.post(f"/api/v1/branches/{branch_closed['id']}/deactivate", json={"version": 1})
    second_membership = memberships[second["id"]]
    api.post(f"/api/v1/application-users/{second_membership['id']}/deactivate", json={"version": 1})
    fake_accounts.reset()
    fake_persons.reset()

    body = api_as(READ, sub=sub).get(URL).json()

    assert body["keycloak_user_id"] == sub
    by_company = {m["company_id"]: m for m in body["memberships"]}
    assert set(by_company) == {first["id"], second["id"]}
    assert by_company[second["id"]]["status"] == "INACTIVE"
    branches = {b["branch_id"]: b for b in by_company[first["id"]]["branches"]}
    assert branches[branch_ok["id"]]["allowed"] is True
    assert branches[branch_closed["id"]] == {
        "branch_id": branch_closed["id"],
        "user_branch_status": "ACTIVE",
        "branch_status": "INACTIVE",
        "allowed": False,
        "reason": "BRANCH_INACTIVE",
    }
    assert fake_accounts.count() == 0 and fake_persons.count() == 0
