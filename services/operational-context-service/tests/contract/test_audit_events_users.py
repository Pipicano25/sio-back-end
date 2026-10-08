"""Eventos de usuarios, asignaciones a sucursal y asesores (feature 016; acciones OC 9–18; T028).

`reference_email` del usuario de aplicación es de una persona natural: solo como marcador y en
`redacted_paths` (DS-09, ampliación 2026-10-07); `display_name` con su valor.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from tests.conftest import update_body

REFERENCE_EMAIL = "compras.persona@correo-ficticio.co"


def _iso(delta: timedelta = timedelta()) -> str:
    return (datetime.now(UTC) + delta).isoformat()


def _clear(test_engine) -> None:
    with test_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE audit_outbox"))


@pytest.fixture
def company(create_company):
    return create_company()


@pytest.fixture
def user(audited_api, company, fake_accounts, fake_persons, test_engine):
    response = audited_api.post(
        f"/api/v1/companies/{company['id']}/application-users",
        json={
            "keycloak_user_id": fake_accounts.add("compras.test"),
            "person_identity_id": str(fake_persons.add()),
            "display_name": "Compras Ficticio",
            "reference_email": REFERENCE_EMAIL,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_application_user_protects_reference_email(user, company, outbox) -> None:
    event = outbox()[-1]

    assert event["action"] == "CREATE_APPLICATION_USER" and event["entity_type"] == "ApplicationUser"
    assert event["entity_id"] == user["id"] and event["company_id"] == company["id"]
    assert event["new_values"]["display_name"] == "Compras Ficticio"
    assert event["new_values"]["reference_email"] == "<registrado>"
    assert "new_values.reference_email" in event["redacted_paths"]
    assert REFERENCE_EMAIL not in repr(event)


def test_update_deactivate_and_reactivate_application_user(audited_api, user, outbox, test_engine) -> None:
    _clear(test_engine)
    url = f"/api/v1/application-users/{user['id']}"
    updated = audited_api.put(
        url, json={"display_name": "Compras Renombrado", "reference_email": REFERENCE_EMAIL, "version": user["version"]},
    )
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert audited_api.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert audited_api.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    update, deactivate, reactivate = outbox()
    assert update["action"] == "UPDATE_APPLICATION_USER"
    assert update["previous_values"] == {"display_name": "Compras Ficticio"}
    assert update["new_values"] == {"display_name": "Compras Renombrado"}
    assert deactivate["action"] == "DEACTIVATE_APPLICATION_USER"
    assert deactivate["new_values"]["status"] == "INACTIVE"
    assert reactivate["action"] == "REACTIVATE_APPLICATION_USER"
    assert reactivate["new_values"]["status"] == "ACTIVE"


def test_user_branch_assignment_lifecycle(audited_api, user, company, create_branch, outbox, test_engine) -> None:
    branch = create_branch(company["id"], code="S-AUD")
    _clear(test_engine)
    assigned = audited_api.post(f"/api/v1/application-users/{user['id']}/user-branches", json={"branch_id": branch["id"]})
    assert assigned.status_code == 201, assigned.text
    assignment = assigned.json()
    url = f"/api/v1/user-branches/{assignment['id']}"
    assert audited_api.post(f"{url}/deactivate", json={"version": assignment["version"]}).status_code == 200
    assert audited_api.post(f"{url}/reactivate", json={"version": assignment["version"] + 1}).status_code == 200

    assign, deactivate, reactivate = outbox()
    assert [assign["action"], deactivate["action"], reactivate["action"]] == [
        "ASSIGN_USER_BRANCH", "DEACTIVATE_USER_BRANCH", "REACTIVATE_USER_BRANCH",
    ]
    for event in (assign, deactivate, reactivate):
        assert event["entity_type"] == "UserBranch" and event["entity_id"] == assignment["id"]
        assert event["company_id"] == company["id"] and event["branch_id"] == branch["id"]
    assert assign["new_values"]["application_user_id"] == user["id"]
    assert deactivate["previous_values"]["status"] == "ACTIVE" and deactivate["new_values"]["status"] == "INACTIVE"


def test_advisor_create_close_and_change_primary(audited_api, company, fake_persons, outbox, test_engine) -> None:
    base = f"/api/v1/companies/{company['id']}/advisor-assignments"
    _clear(test_engine)
    first = audited_api.post(base, json={"person_identity_id": str(fake_persons.add()), "valid_from": _iso(timedelta(days=-30))})
    assert first.status_code == 201, first.text
    current = first.json()
    changed = audited_api.post(
        f"{base}/change-primary",
        json={"current_assignment_id": current["id"], "version": current["version"], "person_identity_id": str(fake_persons.add())},
    )
    assert changed.status_code in (200, 201), changed.text
    new_primary = changed.json()
    new_primary = new_primary["created"]
    closed = audited_api.post(f"/api/v1/advisor-assignments/{new_primary['id']}/close", json={"version": new_primary["version"]})
    assert closed.status_code == 200, closed.text

    create, change, close = outbox()
    assert create["action"] == "CREATE_ADVISOR_ASSIGNMENT" and create["entity_id"] == current["id"]
    assert create["new_values"]["is_primary"] is True
    assert change["action"] == "CHANGE_PRIMARY_ADVISOR_ASSIGNMENT"
    assert change["entity_id"] == new_primary["id"]
    assert change["previous_values"]["previous_primary_id"] == current["id"]
    assert close["action"] == "CLOSE_ADVISOR_ASSIGNMENT" and close["entity_id"] == new_primary["id"]
    assert close["new_values"]["status"] != close["previous_values"]["status"]
    for event in (create, change, close):
        assert event["entity_type"] == "CompanyAdvisorAssignment" and event["company_id"] == company["id"]


def test_update_application_user_reference_email_is_marked(audited_api, user, outbox, test_engine) -> None:
    _clear(test_engine)
    response = audited_api.put(
        f"/api/v1/application-users/{user['id']}",
        json={"display_name": "Compras Ficticio", "reference_email": "otro.correo@correo-ficticio.co", "version": user["version"]},
    )
    assert response.status_code == 200, response.text

    event = outbox()[-1]
    assert event["previous_values"] == {"reference_email": "<modificado>"}
    assert event["new_values"] == {"reference_email": "<modificado>"}
    assert "otro.correo@correo-ficticio.co" not in repr(event) and REFERENCE_EMAIL not in repr(event)
