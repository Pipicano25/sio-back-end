"""Ubicación de empresas por la API (US3; FR-030 a FR-035, RC-05, RC-11, R-03)."""

import logging

import pytest
from sqlalchemy import text

from operational_context_service.observability import SERVICE_LOGGER
from tests.conftest import company_payload, random_uuid

URL = "/api/v1/companies"


def _count(test_engine):
    with test_engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM companies")).scalar_one()


def test_coherent_location_is_stored_as_uuids_only(api, fake_organizations, geo):
    response = api.post(
        URL,
        json=company_payload(fake_organizations.add(), **geo.medellin_location(),
                             latitude=6.244203, longitude=-75.581211, postal_code="050001"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["country_id"] == str(geo.colombia)
    assert body["administrative_division_id"] == str(geo.antioquia)
    assert body["city_id"] == str(geo.medellin)
    assert body["latitude"] == "6.244203" and body["longitude"] == "-75.581211"
    assert not {"country_name", "city_name", "division_name"} & set(body)


def _cases(geo):
    return {
        "pais-inexistente": ({"country_id": random_uuid()}, 422, "COUNTRY_NOT_FOUND", "country_id"),
        "division-inexistente": (
            {"country_id": str(geo.colombia), "administrative_division_id": random_uuid()},
            422, "ADMINISTRATIVE_DIVISION_NOT_FOUND", "administrative_division_id",
        ),
        "ciudad-inexistente": (
            {"country_id": str(geo.colombia), "administrative_division_id": str(geo.antioquia), "city_id": random_uuid()},
            422, "CITY_NOT_FOUND", "city_id",
        ),
        "pais-inactivo": ({"country_id": str(geo.inactive_country)}, 422, "LOCATION_INACTIVE", "country_id"),
        "division-inactiva": (
            {"country_id": str(geo.colombia), "administrative_division_id": str(geo.inactive_division)},
            422, "LOCATION_INACTIVE", "administrative_division_id",
        ),
        "ciudad-inactiva": (
            {"country_id": str(geo.colombia), "administrative_division_id": str(geo.antioquia), "city_id": str(geo.inactive_city)},
            422, "LOCATION_INACTIVE", "city_id",
        ),
        "ciudad-otra-division": (
            {"country_id": str(geo.colombia), "administrative_division_id": str(geo.cundinamarca), "city_id": str(geo.medellin)},
            422, "GEOGRAPHY_INCOHERENT", "city_id",
        ),
        "division-otro-pais": (
            {"country_id": str(geo.peru), "administrative_division_id": str(geo.antioquia)},
            422, "GEOGRAPHY_INCOHERENT", "administrative_division_id",
        ),
        "ciudad-sin-pais": ({"city_id": str(geo.medellin)}, 422, "GEOGRAPHY_PARENT_REQUIRED", "country_id"),
    }


CASE_IDS = [
    "pais-inexistente", "division-inexistente", "ciudad-inexistente", "pais-inactivo",
    "division-inactiva", "ciudad-inactiva", "ciudad-otra-division", "division-otro-pais", "ciudad-sin-pais",
]


@pytest.mark.parametrize("case", CASE_IDS)
def test_rejected_locations(api, fake_organizations, geo, test_engine, caplog, case):
    """Pruebas obligatorias 4 y 6 por la API; C2 (log INFO)."""
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)
    location, status, code, field = _cases(geo)[case]

    response = api.post(URL, json=company_payload(fake_organizations.add(), **location))

    assert response.status_code == status
    body = response.json()
    assert body["code"] == f"OPERATIONAL_CONTEXT.{code}"
    assert body["errors"][0]["field"] == field
    assert _count(test_engine) == 0

    if code != "GEOGRAPHY_PARENT_REQUIRED":
        records = [r for r in caplog.records if r.name == SERVICE_LOGGER and code in r.getMessage()]
        assert records and records[-1].levelno == logging.INFO
        message = records[-1].getMessage()
        assert field in message
        assert records[-1].trace_id == response.headers["x-trace-id"]
        assert "Bearer" not in message and "contacto@" not in message


def test_geography_unavailable_is_503(api, fake_organizations, fake_geography, geo, test_engine):
    """Prueba obligatoria 5 por la API."""
    fake_geography.mode = "unavailable"

    response = api.post(URL, json=company_payload(fake_organizations.add(), **geo.medellin_location()))

    assert response.status_code == 503
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE"
    assert _count(test_engine) == 0


@pytest.mark.parametrize(
    "coordinates, field",
    [
        ({"latitude": 6.2}, "longitude"),
        ({"longitude": -75.5}, "latitude"),
        ({"latitude": 91, "longitude": 0}, "latitude"),
        ({"latitude": 0, "longitude": -180.5}, "longitude"),
        ({"latitude": 6.2442031, "longitude": -75.5}, "latitude"),
    ],
    ids=["sin-longitud", "sin-latitud", "latitud-rango", "longitud-rango", "siete-decimales"],
)
def test_invalid_coordinates(api, fake_organizations, coordinates, field):
    response = api.post(URL, json=company_payload(fake_organizations.add(), **coordinates))

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.VALIDATION_ERROR"
    assert body["errors"][0]["field"] == field


def test_coordinates_are_not_filled_from_city(api, fake_organizations, geo):
    response = api.post(URL, json=company_payload(fake_organizations.add(), **geo.medellin_location()))

    assert response.status_code == 201
    assert response.json()["latitude"] is None and response.json()["longitude"] is None
