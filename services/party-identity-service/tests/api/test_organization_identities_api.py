"""Pruebas de API de alta y consulta de organizaciones (FR-030–FR-032, RC-10, U2)."""

import pytest

from tests.conftest import organization_payload, random_uuid, rule_payload

BASE = "/api/v1/organization-identities"


@pytest.fixture
def nit_rule(api) -> None:
    rule = rule_payload(
        party_kind="ORGANIZATION",
        identification_type="TAX_ID",
        sigla="NIT",
        number_pattern="^[A-Z0-9]{4,11}-[0-9]$",
        number_pattern_description="El NIT lleva guion y dígito de verificación.",
        example_value="900123456-7",
        min_age_years=None,
    )
    assert api.post("/api/v1/identification-type-rules", json=rule).status_code == 201


def _code(response) -> str:
    return response.json()["code"].removeprefix("PARTY_IDENTITY.")


def test_create_returns_201_with_location(api, nit_rule) -> None:
    response = api.post(BASE, json=organization_payload(identification_type="nit"))

    assert response.status_code == 201, response.text
    body = response.json()
    assert response.headers["location"] == f"{BASE}/{body['id']}"
    assert body["status"] == "ACTIVE"
    assert body["identification_type"] == "NIT"


def test_duplicate_is_409(api, nit_rule) -> None:
    assert api.post(BASE, json=organization_payload()).status_code == 201

    response = api.post(BASE, json=organization_payload(legal_name="OTRA"))

    assert response.status_code == 409
    assert _code(response) == "DUPLICATE_IDENTIFICATION"


def test_invalid_number_is_422_with_rule_description(api, nit_rule) -> None:
    response = api.post(BASE, json=organization_payload(identification_number="900000001"))

    assert response.status_code == 422
    assert _code(response) == "INVALID_IDENTIFICATION_NUMBER"
    assert "dígito de verificación" in response.json()["detail"]


def test_unknown_country_is_422(api) -> None:
    response = api.post(BASE, json=organization_payload(country_id=random_uuid()))

    assert response.status_code == 422
    assert _code(response) == "COUNTRY_NOT_FOUND"


def test_geography_unavailable_is_503(api, fake_countries) -> None:
    fake_countries.mode = "unavailable"

    response = api.post(BASE, json=organization_payload())

    assert response.status_code == 503
    assert _code(response) == "DEPENDENCY_UNAVAILABLE"


def test_collection_defaults_to_active(api, nit_rule) -> None:
    created = api.post(BASE, json=organization_payload()).json()
    other = api.post(BASE, json=organization_payload(identification_number="900000002-2")).json()
    api.post(f"{BASE}/{other['id']}/deactivate", json={"version": 1})

    assert [item["id"] for item in api.get(BASE).json()["items"]] == [created["id"]]
    assert [item["id"] for item in api.get(BASE, params={"status": "INACTIVE"}).json()["items"]] == [other["id"]]


def test_invalid_status_filter_is_422(api) -> None:
    response = api.get(BASE, params={"status": "FOO"})

    assert response.status_code == 422
    assert _code(response) == "VALIDATION_ERROR"


@pytest.mark.parametrize("field", ["status", "created_by"])
def test_body_cannot_set_status_or_audit_fields(api, field) -> None:
    response = api.post(BASE, json=organization_payload(**{field: "INACTIVE"}))

    assert response.status_code == 422
    assert _code(response) == "VALIDATION_ERROR"
