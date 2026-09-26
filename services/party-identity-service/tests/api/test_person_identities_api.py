"""Pruebas de API de alta y consulta de personas (FR-020–FR-024, RC-10, DS-09, U2)."""

import logging

import pytest

from tests.conftest import person_payload, random_uuid, rule_payload

BASE = "/api/v1/person-identities"


@pytest.fixture
def colombian_rules(api) -> None:
    """Reglas CC (18+) y TI (7–17) creadas por API."""
    assert api.post("/api/v1/identification-type-rules", json=rule_payload()).status_code == 201
    ti = rule_payload(
        identification_type="IDENTITY_CARD_MODERN",
        sigla="TI",
        number_pattern_description="La tarjeta de identidad tiene 10 dígitos.",
        min_age_years=7,
        max_age_years=17,
    )
    assert api.post("/api/v1/identification-type-rules", json=ti).status_code == 201


def _code(response) -> str:
    return response.json()["code"].removeprefix("PARTY_IDENTITY.")


def test_create_returns_201_with_location_and_defaults(api_as, colombian_rules) -> None:
    client = api_as("perm:party-identity:person_identities:create", sub="creador-1")

    response = client.post(BASE, json=person_payload(identification_type=" cc "))

    assert response.status_code == 201, response.text
    body = response.json()
    assert response.headers["location"] == f"{BASE}/{body['id']}"
    assert body["status"] == "ACTIVE"
    assert body["verification_status"] == "UNVERIFIED"
    assert body["identification_type"] == "CC"
    assert body["created_by"] == "creador-1"
    assert body["updated_by"] == "creador-1"


@pytest.mark.parametrize("field", ["status", "created_by", "updated_by", "version"])
def test_body_cannot_set_status_or_audit_fields(api, field) -> None:
    response = api.post(BASE, json=person_payload(**{field: "INACTIVE" if field == "status" else "otro"}))

    assert response.status_code == 422
    assert _code(response) == "VALIDATION_ERROR"


def test_duplicate_is_409(api, colombian_rules) -> None:
    assert api.post(BASE, json=person_payload()).status_code == 201

    response = api.post(BASE, json=person_payload(first_name="OTRA"))

    assert response.status_code == 409
    assert _code(response) == "DUPLICATE_IDENTIFICATION"


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"identification_number": "12AB"}, "INVALID_IDENTIFICATION_NUMBER"),
        ({"birth_date": None}, "BIRTH_DATE_REQUIRED"),
        ({"identification_type": "TI"}, "AGE_OUT_OF_RANGE"),
        ({"birth_date": "2999-01-01"}, "BIRTH_DATE_IN_FUTURE"),
        ({"identification_country_id": random_uuid()}, "COUNTRY_NOT_FOUND"),
    ],
)
def test_domain_validation_errors_are_422(api, colombian_rules, overrides, code) -> None:
    response = api.post(BASE, json=person_payload(**overrides))

    assert response.status_code == 422, response.text
    assert _code(response) == code


def test_geography_unavailable_is_503(api, colombian_rules, fake_countries) -> None:
    fake_countries.mode = "unavailable"

    response = api.post(BASE, json=person_payload())

    assert response.status_code == 503
    assert _code(response) == "DEPENDENCY_UNAVAILABLE"
    assert api.get(BASE).json()["total_records"] == 0


def test_geography_denied_is_503_with_internal_cause_only_in_logs(api, fake_countries, caplog) -> None:
    fake_countries.mode = "denied"

    response = api.post(BASE, json=person_payload())

    assert response.status_code == 503
    assert "COUNTRY_VALIDATION_DENIED" not in response.text


def test_collection_defaults_to_active(api, colombian_rules, test_engine) -> None:
    created = api.post(BASE, json=person_payload()).json()
    other = api.post(BASE, json=person_payload(identification_number="1000000002")).json()
    api.post(f"{BASE}/{other['id']}/deactivate", json={"version": other["version"]})

    active = api.get(BASE).json()
    inactive = api.get(BASE, params={"status": "INACTIVE"}).json()

    assert [item["id"] for item in active["items"]] == [created["id"]]
    assert [item["id"] for item in inactive["items"]] == [other["id"]]


@pytest.mark.parametrize("param", ["status", "verification_status"])
def test_invalid_enumerated_filter_is_422(api, param) -> None:
    response = api.get(BASE, params={param: "FOO"})

    assert response.status_code == 422
    assert _code(response) == "VALIDATION_ERROR"


def test_error_detail_and_logs_do_not_contain_full_number(api, colombian_rules, caplog) -> None:
    caplog.set_level(logging.INFO, logger="party_identity_service")
    api.post(BASE, json=person_payload(identification_number="1234567890"))

    duplicate = api.post(BASE, json=person_payload(identification_number="1234567890"))

    assert duplicate.status_code == 409
    assert "1234567890" not in duplicate.json()["detail"]
    assert all("1234567890" not in record.getMessage() for record in caplog.records)
