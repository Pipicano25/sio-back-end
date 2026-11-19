"""`PUT` parcial y versión opcional (constitución 4.0.0: Principio VII, D9, D10 y D28).

- El `PUT` recibe solo los campos que cambian; un campo ausente no cambia.
- `null` borra un campo opcional; en un campo obligatorio responde `422`.
- Un cuerpo vacío o solo con `version` responde `422`.
- `version` es opcional: si llega y no coincide, `409`; si no llega, gana la última escritura.
- Inactivar y reactivar no exigen versión ni cuerpo.
"""

import pytest


def _company_url(company):
    return f"/api/v1/companies/{company['id']}"


def _branch_url(branch):
    return f"/api/v1/branches/{branch['id']}"


def test_company_put_with_one_field_keeps_the_rest(api, create_company):
    company = create_company()

    response = api.put(_company_url(company), json={"phone": "+57 2 555 0101"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["phone"] == "+57 2 555 0101"
    for field in ("organization_identity_id", "email", "address_line", "city_id", "timezone", "default_currency"):
        assert body[field] == company[field]
    assert body["version"] == company["version"] + 1


def test_company_put_without_version_applies_over_current(api, create_company):
    company = create_company()
    api.put(_company_url(company), json={"phone": "1"})

    response = api.put(_company_url(company), json={"phone": "2"})

    assert response.status_code == 200, response.text
    assert response.json()["phone"] == "2"


def test_company_put_with_stale_version_is_409(api, create_company):
    company = create_company()
    api.put(_company_url(company), json={"phone": "1"})

    response = api.put(_company_url(company), json={"phone": "2", "version": company["version"]})

    assert response.status_code == 409
    assert api.get(_company_url(company)).json()["phone"] == "1"


def test_company_null_clears_optional_and_rejects_required(api, create_company):
    company = create_company()

    cleared = api.put(_company_url(company), json={"phone": None})
    rejected = api.put(_company_url(company), json={"default_currency": None})

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["phone"] is None
    assert rejected.status_code == 422


@pytest.mark.parametrize("body", [{}, {"version": 1}])
def test_company_body_without_fields_is_422(api, create_company, body):
    company = create_company()

    assert api.put(_company_url(company), json=body).status_code == 422


def test_company_status_actions_without_body(api, create_company):
    company = create_company()

    deactivated = api.post(f"{_company_url(company)}/deactivate")
    reactivated = api.post(f"{_company_url(company)}/reactivate", json={})

    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "INACTIVE"
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["status"] == "ACTIVE"


def test_branch_put_with_one_field_keeps_the_rest(api, create_company, create_branch):
    company = create_company()
    branch = create_branch(company["id"])

    response = api.put(_branch_url(branch), json={"name": "Sucursal renombrada"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Sucursal renombrada"
    assert body["code"] == branch["code"] and body["city_id"] == branch["city_id"]


def test_branch_null_code_is_422_and_status_actions_without_body(api, create_company, create_branch):
    company = create_company()
    branch = create_branch(company["id"])

    assert api.put(_branch_url(branch), json={"code": None}).status_code == 422
    assert api.post(f"{_branch_url(branch)}/deactivate").json()["status"] == "INACTIVE"
    assert api.post(f"{_branch_url(branch)}/reactivate").json()["status"] == "ACTIVE"


def test_application_user_put_changes_only_email(api, create_company, fake_accounts, fake_persons):
    company = create_company()
    fake_accounts.add("parcial")
    user = api.post(
        f"/api/v1/companies/{company['id']}/application-users",
        json={"username": "parcial", "person_identity_id": str(fake_persons.add()), "display_name": "Usuario parcial"},
    ).json()

    response = api.put(f"/api/v1/application-users/{user['id']}", json={"reference_email": "parcial@dao.com.co"})

    assert response.status_code == 200, response.text
    assert response.json()["reference_email"] == "parcial@dao.com.co"
    assert response.json()["display_name"] == "Usuario parcial"
    assert api.put(f"/api/v1/application-users/{user['id']}", json={"display_name": None}).status_code == 422
    assert api.post(f"/api/v1/application-users/{user['id']}/deactivate").status_code == 200
