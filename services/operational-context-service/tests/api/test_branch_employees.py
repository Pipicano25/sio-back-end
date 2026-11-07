"""Empleados de una empresa separados por sucursal (FR-025a de la feature 005)."""

import pytest

READ = (
    "perm:operational-context:user_branches:read",
    "perm:operational-context:branches:read",
    "perm:operational-context:application_users:read",
)


def url(company_id: str) -> str:
    return f"/api/v1/companies/{company_id}/branch-employees"


@pytest.fixture
def company_with_staff(api, create_company, create_branch, fake_accounts, fake_persons):
    """Empresa con tres sucursales: dos empleados en PRINCIPAL, uno también en NORTE y SUR vacía."""
    company = create_company()
    principal = create_branch(company["id"], code="PRINCIPAL", name="Sede Principal")
    norte = create_branch(company["id"], code="NORTE", name="Sede Norte")
    sur = create_branch(company["id"], code="SUR", name="Sede Sur")
    users = []
    for username, display_name in (("compras.test", "Ana Compras"), ("ventas.test", "Luis Ventas")):
        response = api.post(
            f"/api/v1/companies/{company['id']}/application-users",
            json={
                "keycloak_user_id": fake_accounts.add(username),
                "person_identity_id": str(fake_persons.add()),
                "display_name": display_name,
                "reference_email": f"{username}@empresa-ficticia.co",
            },
        )
        assert response.status_code == 201, response.text
        users.append(response.json())
    assignments = {}
    for user, branch in ((users[0], principal), (users[1], principal), (users[1], norte)):
        response = api.post(f"/api/v1/application-users/{user['id']}/user-branches", json={"branch_id": branch["id"]})
        assert response.status_code == 201, response.text
        assignments[(user["id"], branch["id"])] = response.json()
    fake_accounts.reset()
    fake_persons.reset()
    return {
        "company": company,
        "principal": principal,
        "norte": norte,
        "sur": sur,
        "users": users,
        "assignments": assignments,
    }


def _by_code(body):
    return {item["code"]: item for item in body["items"]}


def test_lists_branches_with_their_employees(api, company_with_staff, fake_persons):
    data = company_with_staff
    response = api.get(url(data["company"]["id"]))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_records"] == 3 and body["page"] == 1
    groups = _by_code(body)
    assert set(groups) == {"PRINCIPAL", "NORTE", "SUR"}
    assert groups["PRINCIPAL"]["name"] == "Sede Principal"
    assert groups["PRINCIPAL"]["branch_id"] == data["principal"]["id"]
    assert groups["PRINCIPAL"]["status"] == "ACTIVE"
    assert [e["display_name"] for e in groups["PRINCIPAL"]["employees"]] == ["Ana Compras", "Luis Ventas"]
    assert [e["display_name"] for e in groups["NORTE"]["employees"]] == ["Luis Ventas"]
    assert groups["SUR"]["employees"] == []

    ana = groups["PRINCIPAL"]["employees"][0]
    user = data["users"][0]
    assignment = data["assignments"][(user["id"], data["principal"]["id"])]
    tag = user["person_identity_id"][:8].upper()
    assert ana == {
        "application_user_id": user["id"],
        "display_name": "Ana Compras",
        "reference_email": "compras.test@empresa-ficticia.co",
        "keycloak_user_id": user["keycloak_user_id"],
        "person_identity_id": user["person_identity_id"],
        "identification_type": "CC",
        "identification_number": ana["identification_number"],
        "first_name": f"Nombre {tag}",
        "middle_name": None,
        "last_name": f"Apellido {tag}",
        "second_last_name": None,
        "membership_status": "ACTIVE",
        "user_branch_id": assignment["id"],
        "user_branch_status": "ACTIVE",
        "assigned_at": assignment["assigned_at"],
        "allowed": True,
        "reason": None,
    }
    # Una consulta a Party Identity por persona, aunque esté en dos sucursales.
    assert fake_persons.count("get_person_profile") == 2


def test_party_identity_unavailable_keeps_listing_without_person_data(api, company_with_staff, fake_persons):
    fake_persons.mode = "unavailable"

    response = api.get(url(company_with_staff["company"]["id"]))

    assert response.status_code == 200
    employee = _by_code(response.json())["PRINCIPAL"]["employees"][0]
    assert employee["display_name"] == "Ana Compras"
    assert employee["first_name"] is None and employee["identification_number"] is None
    # Ante la primera falla deja de consultar.
    assert fake_persons.count("get_person_profile") == 1


def test_filter_by_branch_and_search(api, company_with_staff):
    data = company_with_staff
    only_norte = api.get(url(data["company"]["id"]), params={"branch_id": data["norte"]["id"]}).json()
    by_search = api.get(url(data["company"]["id"]), params={"search": "principal"}).json()

    assert [item["code"] for item in only_norte["items"]] == ["NORTE"]
    assert only_norte["total_records"] == 1
    assert [item["code"] for item in by_search["items"]] == ["PRINCIPAL"]


def test_inactive_assignments_and_branches_are_filtered_by_status(api, company_with_staff):
    data = company_with_staff
    luis = data["users"][1]
    assignment = data["assignments"][(luis["id"], data["norte"]["id"])]
    api.post(f"/api/v1/user-branches/{assignment['id']}/deactivate", json={"version": assignment["version"]})
    api.post(f"/api/v1/branches/{data['sur']['id']}/deactivate", json={"version": data["sur"]["version"]})

    active = _by_code(api.get(url(data["company"]["id"])).json())
    retired = _by_code(api.get(url(data["company"]["id"]), params={"assignment_status": "INACTIVE"}).json())
    inactive_branches = _by_code(api.get(url(data["company"]["id"]), params={"status": "INACTIVE"}).json())

    assert set(active) == {"PRINCIPAL", "NORTE"}
    assert active["NORTE"]["employees"] == []
    retired_employee = retired["NORTE"]["employees"][0]
    assert retired_employee["display_name"] == "Luis Ventas"
    assert retired_employee["user_branch_status"] == "INACTIVE"
    assert retired_employee["allowed"] is False and retired_employee["reason"]
    assert set(inactive_branches) == {"SUR"}


def test_pagination_is_by_branch(api, company_with_staff):
    body = api.get(url(company_with_staff["company"]["id"]), params={"page_size": 2}).json()

    assert len(body["items"]) == 2
    assert body["total_records"] == 3 and body["total_pages"] == 2


def test_member_reads_own_company_but_not_another(api, api_as, company_with_staff, create_company):
    data = company_with_staff
    member = api_as(*READ, sub=data["users"][0]["keycloak_user_id"])
    other = create_company()

    assert member.get(url(data["company"]["id"])).status_code == 200
    response = member.get(url(other["id"]))
    assert response.status_code == 404
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.NOT_FOUND"


def test_unknown_company_or_foreign_branch_is_404(api, company_with_staff, create_company, create_branch):
    other = create_company()
    foreign = create_branch(other["id"], code="X-1")

    unknown = api.get(url("00000000-0000-4000-8000-000000000099"))
    mismatch = api.get(url(company_with_staff["company"]["id"]), params={"branch_id": foreign["id"]})

    assert unknown.status_code == 404
    assert mismatch.status_code == 404
    assert mismatch.json()["detail"] == "La sucursal solicitada no existe."


@pytest.mark.parametrize("missing", READ)
def test_requires_the_three_read_permissions(api_as, company_with_staff, missing):
    permissions = [permission for permission in READ if permission != missing]
    client = api_as(*permissions, "perm:operational-context:platform:administer")

    assert client.get(url(company_with_staff["company"]["id"])).status_code == 403
