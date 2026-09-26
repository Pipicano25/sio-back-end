"""Consulta y modificación de usuarios operativos (US1; FR-013, FR-015, FR-082; RC-09)."""

import pytest


@pytest.fixture
def register(api, fake_accounts, fake_persons):
    def _register(company_id, username, **overrides):
        body = {
            "username": username,
            "person_identity_id": str(fake_persons.add()),
            "display_name": overrides.pop("display_name", f"Usuario {username}"),
            **overrides,
        }
        fake_accounts.add(username)
        response = api.post(f"/api/v1/companies/{company_id}/application-users", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    return _register


def test_collection_filters_and_pagination(api, create_company, register):
    company = create_company()
    ana = register(company["id"], "ana", display_name="Ana Ficticia", reference_email="ana@ficticia.co")
    register(company["id"], "beto", display_name="Beto Ficticio")
    inactive = register(company["id"], "carla")
    api.post(f"/api/v1/application-users/{inactive['id']}/deactivate", json={"version": 1})
    url = f"/api/v1/companies/{company['id']}/application-users"

    default = api.get(url).json()
    assert default["total_records"] == 2
    assert {item["status"] for item in default["items"]} == {"ACTIVE"}

    assert api.get(url, params={"status": "INACTIVE"}).json()["total_records"] == 1
    assert [i["id"] for i in api.get(url, params={"search": "FICTICIA"}).json()["items"]] == [ana["id"]]
    assert api.get(url, params={"search": "ana@"}).json()["total_records"] == 1
    assert api.get(url, params={"keycloak_user_id": ana["keycloak_user_id"]}).json()["total_records"] == 1
    assert api.get(url, params={"person_identity_id": ana["person_identity_id"]}).json()["total_records"] == 1

    page = api.get(url, params={"page": 2, "page_size": 1}).json()
    assert page["page"] == 2 and page["total_pages"] == 2 and len(page["items"]) == 1

    assert api.get(url, params={"status": "OTRO"}).status_code == 422


def test_get_by_uuid_in_any_status(api, create_company, register):
    user = register(create_company()["id"], "dora")
    api.post(f"/api/v1/application-users/{user['id']}/deactivate", json={"version": 1})

    response = api.get(f"/api/v1/application-users/{user['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"
    assert response.json()["company_status"] == "ACTIVE"


def test_get_unknown_is_404_and_malformed_is_422(api):
    assert api.get("/api/v1/application-users/00000000-0000-4000-8000-000000000001").status_code == 404
    assert api.get("/api/v1/application-users/no-uuid").status_code == 422


def test_put_updates_reference_data_with_version(
    api, create_company, register, fake_accounts, fake_persons
):
    user = register(create_company()["id"], "eva")
    fake_accounts.reset()
    fake_persons.reset()

    response = api.put(
        f"/api/v1/application-users/{user['id']}",
        json={"display_name": "Eva Nueva", "reference_email": "eva@ficticia.co", "version": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Eva Nueva" and body["version"] == 2
    assert fake_accounts.count() == 0 and fake_persons.count() == 0


def test_put_with_stale_version_is_409(api, create_company, register):
    user = register(create_company()["id"], "fabio")
    url = f"/api/v1/application-users/{user['id']}"
    api.put(url, json={"display_name": "Cambio", "version": 1})

    response = api.put(url, json={"display_name": "Otro", "version": 1})

    assert response.status_code == 409
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.VERSION_CONFLICT"


def test_identical_put_does_not_change_version_or_audit(api, create_company, register):
    user = register(create_company()["id"], "gina", reference_email="gina@ficticia.co")

    response = api.put(
        f"/api/v1/application-users/{user['id']}",
        json={"display_name": user["display_name"], "reference_email": "gina@ficticia.co", "version": 1},
    )

    assert response.status_code == 200
    assert response.json()["version"] == 1
    assert response.json()["updated_at"] == user["updated_at"]


@pytest.mark.parametrize("field", ["keycloak_user_id", "person_identity_id", "company_id"])
def test_put_immutable_fields_is_422(api, create_company, register, field):
    user = register(create_company()["id"], "hugo")

    response = api.put(
        f"/api/v1/application-users/{user['id']}",
        json={"display_name": "Hugo", "version": 1, field: "00000000-0000-4000-8000-000000000001"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.IMMUTABLE_FIELD"
    assert body["errors"][0]["field"] == field
