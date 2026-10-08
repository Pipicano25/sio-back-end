"""Eventos de auditoría de empresas y sucursales (feature 016; acciones OC 1–8; DS-09; T027).

Cada escritura registra exactamente un evento en la outbox, en la misma transacción, con acción,
tipo, entidad, alcance, autor, solicitud y valores. Correo, teléfono, dirección, código postal y
coordenadas de la sede nunca salen con su valor: van como marcador y en `redacted_paths`.
"""

from __future__ import annotations

import logging

import pytest

from tests.conftest import AUDIT_SUB, AUDIT_USERNAME, branch_payload, company_payload, update_body

SENSITIVE_VALUES = ("contacto@empresa-ficticia.co", "+57 604 000 0000", "Calle Ficticia 1 # 2-3", "050021")
CONTACT = ("email", "phone", "address_line", "postal_code", "latitude", "longitude")


def _single(outbox):
    events = outbox()
    assert len(events) == 1, events
    return events[0]


@pytest.fixture
def company(audited_api, fake_organizations, outbox, test_engine):
    response = audited_api.post(
        "/api/v1/companies",
        json=company_payload(fake_organizations.add(), postal_code="050021", latitude="6.244203", longitude="-75.581211"),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _clear(test_engine):
    from sqlalchemy import text

    with test_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE audit_outbox"))


def test_create_company_event_with_protected_contact(company, outbox, caplog) -> None:
    event = _single(outbox)

    assert event["action"] == "CREATE_COMPANY" and event["entity_type"] == "Company"
    assert event["entity_id"] == company["id"] and event["company_id"] == company["id"]
    assert event["branch_id"] is None and event["result"] == "SUCCESS"
    assert event["keycloak_user_id"] == AUDIT_SUB and event["username_snapshot"] == AUDIT_USERNAME
    assert event["previous_values"] is None
    values = event["new_values"]
    assert values["organization_identity_id"] == company["organization_identity_id"]
    assert values["default_currency"] == company["default_currency"] and values["status"] == "ACTIVE"
    for field in CONTACT:
        assert values[field] == "<registrado>"
        assert f"new_values.{field}" in event["redacted_paths"]
    assert not set(values) & {"id", "version", "created_at", "created_by", "updated_at", "updated_by"}
    serialized = repr(event)
    assert not any(value in serialized for value in SENSITIVE_VALUES)


def test_update_company_records_only_changed_fields(audited_api, company, outbox, test_engine) -> None:
    _clear(test_engine)
    response = audited_api.put(
        f"/api/v1/companies/{company['id']}",
        json=update_body(company, email="nuevo@empresa-ficticia.co", timezone="America/Lima"),
    )
    assert response.status_code == 200, response.text

    event = _single(outbox)
    assert event["action"] == "UPDATE_COMPANY" and event["company_id"] == company["id"]
    assert event["previous_values"] == {"email": "<modificado>", "timezone": company["timezone"]}
    assert event["new_values"] == {"email": "<modificado>", "timezone": "America/Lima"}
    assert sorted(event["redacted_paths"]) == ["new_values.email", "previous_values.email"]
    assert "nuevo@empresa-ficticia.co" not in repr(event)


def test_identical_update_records_nothing(audited_api, company, outbox, test_engine) -> None:
    _clear(test_engine)

    response = audited_api.put(f"/api/v1/companies/{company['id']}", json=update_body(company))

    assert response.status_code == 200
    assert outbox() == []


def test_removing_a_protected_value_is_marked_as_removed(audited_api, company, outbox, test_engine) -> None:
    _clear(test_engine)
    response = audited_api.put(f"/api/v1/companies/{company['id']}", json=update_body(company, phone=None))
    assert response.status_code == 200, response.text

    event = _single(outbox)
    assert event["previous_values"] == {"phone": "<eliminado>"}
    assert event["new_values"] == {"phone": None}
    assert event["redacted_paths"] == ["previous_values.phone"]


def test_deactivate_and_reactivate_company(audited_api, company, outbox, test_engine) -> None:
    _clear(test_engine)
    url = f"/api/v1/companies/{company['id']}"
    assert audited_api.post(f"{url}/deactivate", json={"version": company["version"]}).status_code == 200
    assert audited_api.post(f"{url}/reactivate", json={"version": company["version"] + 1}).status_code == 200

    deactivate, reactivate = outbox()
    assert deactivate["action"] == "DEACTIVATE_COMPANY"
    assert deactivate["previous_values"]["status"] == "ACTIVE" and deactivate["new_values"]["status"] == "INACTIVE"
    assert reactivate["action"] == "REACTIVATE_COMPANY"
    assert reactivate["previous_values"]["status"] == "INACTIVE" and reactivate["new_values"]["status"] == "ACTIVE"
    assert {deactivate["company_id"], reactivate["company_id"]} == {company["id"]}


@pytest.fixture
def branch(audited_api, company, test_engine):
    response = audited_api.post(
        f"/api/v1/companies/{company['id']}/branches",
        json=branch_payload(email="sede@empresa-ficticia.co", phone="+57 604 111 1111"),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_branch_event(branch, company, outbox) -> None:
    event = outbox()[-1]

    assert event["action"] == "CREATE_BRANCH" and event["entity_type"] == "Branch"
    assert event["entity_id"] == branch["id"]
    assert event["company_id"] == company["id"] and event["branch_id"] == branch["id"]
    assert event["new_values"]["code"] == branch["code"] and event["new_values"]["name"] == branch["name"]
    assert event["new_values"]["email"] == "<registrado>" and event["new_values"]["phone"] == "<registrado>"
    assert "sede@empresa-ficticia.co" not in repr(event)


def test_update_deactivate_and_reactivate_branch(audited_api, branch, outbox, test_engine) -> None:
    _clear(test_engine)
    url = f"/api/v1/branches/{branch['id']}"
    updated = audited_api.put(url, json=update_body(branch, name="Sucursal Renombrada"))
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert audited_api.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert audited_api.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    update, deactivate, reactivate = outbox()
    assert update["action"] == "UPDATE_BRANCH"
    assert update["previous_values"] == {"name": branch["name"]}
    assert update["new_values"] == {"name": "Sucursal Renombrada"}
    assert [deactivate["action"], reactivate["action"]] == ["DEACTIVATE_BRANCH", "REACTIVATE_BRANCH"]
    for event in (update, deactivate, reactivate):
        assert event["branch_id"] == branch["id"] and event["company_id"] == branch["company_id"]


def test_protected_values_never_reach_the_logs(audited_api, fake_organizations, caplog) -> None:
    with caplog.at_level(logging.DEBUG):
        response = audited_api.post("/api/v1/companies", json=company_payload(fake_organizations.add()))
    assert response.status_code == 201

    assert not any(value in caplog.text for value in SENSITIVE_VALUES)
