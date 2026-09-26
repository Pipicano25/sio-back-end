"""Alta de sucursales (US4; FR-020 a FR-022, RN-01, RN-09; pruebas obligatorias 8 y 12)."""

import pytest
from sqlalchemy import text

from tests.conftest import branch_payload, random_uuid


def _url(company_id):
    return f"/api/v1/companies/{company_id}/branches"


def _branch_count(test_engine):
    with test_engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM branches")).scalar_one()


def test_create_under_active_company(api_as, create_company, fake_organizations):
    company = create_company()
    fake_organizations.reset()
    client = api_as("perm:operational-context:branches:create", sub="sup-1")

    response = client.post(_url(company["id"]), json=branch_payload(code=" med-01 "))

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"/api/v1/branches/{body['id']}"
    assert body["code"] == "MED-01"
    assert body["company_id"] == company["id"]
    assert body["company_status"] == "ACTIVE"
    assert body["status"] == "ACTIVE"
    assert body["version"] == 1
    assert body["created_by"] == "sup-1"
    assert fake_organizations.count() == 0  # las sucursales nunca consultan Party Identity


def test_duplicate_code_in_same_company(api, create_company, create_branch):
    company = create_company()
    create_branch(company["id"], code="BOG-01")

    response = api.post(_url(company["id"]), json=branch_payload(code=" bog-01 "))

    assert response.status_code == 409
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.DUPLICATE_BRANCH_CODE"


def test_duplicate_code_against_inactive_branch(api, create_company, create_branch):
    company = create_company()
    branch = create_branch(company["id"], code="BOG-01")
    api.post(f"/api/v1/branches/{branch['id']}/deactivate", json={"version": 1})

    response = api.post(_url(company["id"]), json=branch_payload(code="BOG-01"))

    assert response.status_code == 409


def test_same_code_in_other_company(api, create_company, create_branch):
    first, second = create_company(), create_company()
    create_branch(first["id"], code="BOG-01")

    response = api.post(_url(second["id"]), json=branch_payload(code="BOG-01"))

    assert response.status_code == 201


def test_unknown_company_is_404(api):
    response = api.post(_url(random_uuid()), json=branch_payload())

    assert response.status_code == 404
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.NOT_FOUND"


def test_inactive_company_is_422(api, create_company, test_engine):
    """Prueba obligatoria 8 (alta)."""
    company = create_company()
    api.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": 1})

    response = api.post(_url(company["id"]), json=branch_payload())

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.COMPANY_INACTIVE"
    assert _branch_count(test_engine) == 0


def test_company_id_in_body_is_rejected(api, create_company):
    first, second = create_company(), create_company()

    response = api.post(_url(first["id"]), json=branch_payload(company_id=second["id"]))

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "company_id"


def test_invalid_location_uses_geography_codes(api, create_company, geo):
    company = create_company()

    response = api.post(
        _url(company["id"]),
        json=branch_payload(country_id=str(geo.colombia), administrative_division_id=str(geo.cundinamarca),
                            city_id=str(geo.medellin)),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.GEOGRAPHY_INCOHERENT"


def test_geography_unavailable_is_503(api, create_company, fake_geography, geo, test_engine):
    company = create_company()
    fake_geography.mode = "unavailable"

    response = api.post(_url(company["id"]), json=branch_payload(**geo.medellin_location()))

    assert response.status_code == 503
    assert _branch_count(test_engine) == 0


@pytest.mark.parametrize("unknown_field", ["created_by", "status", "company_status", "effective_timezone", "foo"])
def test_unknown_fields_are_422(api, create_company, unknown_field):
    """Prueba obligatoria 12."""
    company = create_company()

    response = api.post(_url(company["id"]), json=branch_payload(**{unknown_field: "x"}))

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == unknown_field


@pytest.mark.parametrize("payload, field", [
    ({"code": "   "}, "code"),
    ({"code": "X" * 41}, "code"),
    ({"name": "  "}, "name"),
    ({"name": "N" * 161}, "name"),
    ({"timezone": "Bogota"}, "timezone"),
])
def test_invalid_fields(api, create_company, payload, field):
    company = create_company()

    response = api.post(_url(company["id"]), json=branch_payload(**payload))

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == field
