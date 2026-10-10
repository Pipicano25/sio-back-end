"""Integridad del país de las reglas de identificación frente a Geography (G-017-01).

Única operación que fija `country_id`: `POST /identification-type-rules` (consulta Geography). En
`PUT` el país es inmutable (`422 IMMUTABLE_FIELD`) y `/versions` hereda el de la regla. Semántica:
país inexistente → `422 COUNTRY_NOT_FOUND`; Geography no disponible → `503
DEPENDENCY_UNAVAILABLE`. Un rechazo no escribe la regla ni registra evento de auditoría.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from tests.conftest import COLOMBIA_ID, rule_payload

BASE = "/api/v1/identification-type-rules"


def _code(response) -> str:
    return response.json()["code"].removeprefix("PARTY_IDENTITY.")


def _rules(api) -> list[dict]:
    return api.get(BASE, params={"page_size": 100}).json()["items"]


def _create(api) -> dict:
    response = api.post(BASE, json=rule_payload())
    assert response.status_code == 201, response.text
    return response.json()


def test_create_with_existing_country_succeeds_and_records_audit(api, fake_countries, outbox, clear_outbox) -> None:
    clear_outbox()

    response = api.post(BASE, json=rule_payload())

    assert response.status_code == 201, response.text
    rule = response.json()
    assert rule["country_id"] == str(COLOMBIA_ID)
    assert ("exists", COLOMBIA_ID) in fake_countries.calls
    assert [item["id"] for item in _rules(api)] == [rule["id"]]
    (event,) = outbox()
    assert event["action"] == "CREATE_IDENTIFICATION_TYPE_RULE"
    assert event["entity_id"] == rule["id"] and event["result"] == "SUCCESS"


def test_create_with_unknown_country_is_422_without_write_or_audit(api, fake_countries, outbox, clear_outbox) -> None:
    clear_outbox()
    unknown = uuid4()

    response = api.post(BASE, json=rule_payload(country_id=str(unknown)))

    assert response.status_code == 422, response.text
    assert _code(response) == "COUNTRY_NOT_FOUND"
    assert ("exists", unknown) in fake_countries.calls
    assert _rules(api) == []
    assert outbox() == []


@pytest.mark.parametrize("mode", ["unavailable", "denied"])
def test_create_with_geography_down_is_503_without_write_or_audit(api, fake_countries, outbox, clear_outbox, mode) -> None:
    clear_outbox()
    fake_countries.mode = mode

    response = api.post(BASE, json=rule_payload())

    assert response.status_code == 503, response.text
    assert _code(response) == "DEPENDENCY_UNAVAILABLE"
    assert response.json()["dependency"] == "geography"
    fake_countries.mode = "ok"
    assert _rules(api) == []
    assert outbox() == []


@pytest.mark.parametrize("target", ["existing", "unknown"])
def test_put_cannot_change_country(api, fake_countries, outbox, clear_outbox, target) -> None:
    rule = _create(api)
    other = uuid4()
    if target == "existing":
        fake_countries.countries[other] = "PER"
    clear_outbox()
    fake_countries.calls.clear()

    response = api.put(f"{BASE}/{rule['id']}", json={
        "country_id": str(other),
        "number_pattern_description": "Descripción nueva.",
        "example_value": rule["example_value"],
        "version": rule["version"],
    })

    assert response.status_code == 422, response.text
    assert _code(response) == "IMMUTABLE_FIELD"
    assert fake_countries.calls == []
    current = api.get(f"{BASE}/{rule['id']}").json()
    assert current["country_id"] == str(COLOMBIA_ID)
    assert current["version"] == rule["version"]
    assert current["number_pattern_description"] == rule["number_pattern_description"]
    assert outbox() == []


def test_put_with_same_country_succeeds_and_records_audit(api, outbox, clear_outbox) -> None:
    rule = _create(api)
    clear_outbox()

    response = api.put(f"{BASE}/{rule['id']}", json={
        "country_id": str(COLOMBIA_ID),
        "number_pattern_description": "Descripción nueva.",
        "example_value": rule["example_value"],
        "version": rule["version"],
    })

    assert response.status_code == 200, response.text
    assert response.json()["country_id"] == str(COLOMBIA_ID)
    (event,) = outbox()
    assert event["action"] == "UPDATE_IDENTIFICATION_TYPE_RULE" and event["result"] == "SUCCESS"


def test_new_version_keeps_country_without_calling_geography(api, fake_countries) -> None:
    rule = _create(api)
    fake_countries.calls.clear()

    response = api.post(f"{BASE}/{rule['id']}/versions", json={
        "number_pattern": "^[0-9]{8,10}$",
        "number_pattern_description": "Patrón ampliado.",
        "example_value": "12345678",
        "min_age_years": 18,
        "version": rule["version"],
    })

    assert response.status_code == 201, response.text
    assert response.json()["country_id"] == str(COLOMBIA_ID)
    assert fake_countries.calls == []


def test_failure_after_validation_rolls_back_rule_and_event(api, outbox, clear_outbox) -> None:
    clear_outbox()

    with patch(
        "party_identity_service.application.audit_events.record_audit_event",
        side_effect=RuntimeError("fallo simulado al escribir la outbox"),
    ):
        response = api.post(BASE, json=rule_payload())

    assert response.status_code == 500
    assert _rules(api) == []
    assert outbox() == []
