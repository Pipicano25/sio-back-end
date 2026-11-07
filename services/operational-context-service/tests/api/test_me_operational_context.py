"""Contexto operativo propio (US4; FR-070, FR-070a)."""

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
    closed = branches[branch_closed["id"]]
    assert {key: closed[key] for key in ("branch_id", "user_branch_status", "branch_status", "allowed", "reason")} == {
        "branch_id": branch_closed["id"],
        "user_branch_status": "ACTIVE",
        "branch_status": "INACTIVE",
        "allowed": False,
        "reason": "BRANCH_INACTIVE",
    }
    assert (closed["code"], closed["name"]) == ("CERRADA", "Sucursal Ficticia Medellín")
    assert fake_accounts.count() == 0 and fake_persons.count() == 0


def _member_of(api, fake_accounts, fake_persons, company, branch):
    sub = fake_accounts.add("ventas.test")
    person = str(fake_persons.add())
    user = api.post(
        f"/api/v1/companies/{company['id']}/application-users",
        json={"keycloak_user_id": sub, "person_identity_id": person, "display_name": "V"},
    ).json()
    api.post(f"/api/v1/application-users/{user['id']}/user-branches", json={"branch_id": branch["id"]})
    return sub


def test_company_and_branch_details(
    api, api_as, create_company, create_branch, fake_accounts, fake_organizations, fake_persons
):
    company = create_company()
    branch = create_branch(company["id"], code="CENTRO", name="Sede Centro", phone="+57 604 111 2233")
    sub = _member_of(api, fake_accounts, fake_persons, company, branch)
    fake_organizations.reset()

    membership = api_as(READ, sub=sub).get(URL).json()["memberships"][0]

    tag = company["organization_identity_id"][:8].upper()
    assert membership["company"] == {
        "id": company["id"],
        "organization_identity_id": company["organization_identity_id"],
        "legal_name": f"EMPRESA {tag} S.A.S.",
        "trade_name": f"EMPRESA {tag}",
        "identification_type": "NIT",
        "identification_number": "900123456",
        "email": "contacto@empresa-ficticia.co",
        "phone": "+57 604 000 0000",
        "address_line": "Calle Ficticia 1 # 2-3",
        "country_id": None,
        "administrative_division_id": None,
        "city_id": None,
        "postal_code": None,
        "timezone": company["timezone"],
        "default_currency": company["default_currency"],
        "status": "ACTIVE",
    }
    only = membership["branches"][0]
    assert (only["branch_id"], only["code"], only["name"], only["phone"]) == (
        branch["id"], "CENTRO", "Sede Centro", "+57 604 111 2233"
    )
    assert only["timezone"] == company["timezone"]
    assert fake_organizations.count("get_organization_profile") == 1


def test_party_identity_unavailable_keeps_context_without_company_name(
    api, api_as, create_company, create_branch, fake_accounts, fake_organizations, fake_persons
):
    company = create_company()
    branch = create_branch(company["id"])
    sub = _member_of(api, fake_accounts, fake_persons, company, branch)
    fake_organizations.mode = "unavailable"

    response = api_as(READ, sub=sub).get(URL)

    assert response.status_code == 200
    membership = response.json()["memberships"][0]
    assert membership["company"]["id"] == company["id"]
    assert membership["company"]["legal_name"] is None
    assert membership["company"]["trade_name"] is None
    assert membership["branches"][0]["allowed"] is True
