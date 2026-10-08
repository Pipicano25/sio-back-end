"""Rechazos sin evento y atomicidad cambio + outbox (feature 016; DS-02, RC-01, RC-06; T029)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sio_audit import outbox as sio_outbox
from sqlalchemy import text

from tests.conftest import company_payload, update_body


def _count(test_engine, table: str) -> int:
    with test_engine.connect() as connection:
        return connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def test_rejections_record_no_event(audited_api, anonymous, api_as, create_company, fake_organizations, outbox) -> None:
    company = create_company()
    before = len(outbox())
    url = f"/api/v1/companies/{company['id']}"

    assert anonymous.post("/api/v1/companies", json=company_payload(fake_organizations.add())).status_code == 401
    assert api_as("perm:operational-context:companies:read").put(url, json=update_body(company, timezone="America/Lima")).status_code == 403
    assert audited_api.put(f"/api/v1/companies/{company['id'][:-1]}0", json=update_body(company)).status_code in (404, 422)
    assert audited_api.put(url, json=update_body(company, timezone="America/Lima", version=99)).status_code == 409
    assert audited_api.put(url, json=update_body(company, timezone="Zona/Inexistente")).status_code == 422
    assert audited_api.post("/api/v1/companies", json=company_payload(company["organization_identity_id"])).status_code == 409

    assert len(outbox()) == before


def test_responses_are_unchanged_by_auditing(audited_api, create_company) -> None:
    company = create_company()

    response = audited_api.put(f"/api/v1/companies/{company['id']}", json=update_body(company, timezone="America/Lima"))

    assert response.status_code == 200
    assert set(response.json()) == set(company)


def test_failure_after_recording_rolls_back_change_and_event(audited_api, create_company, outbox, test_engine) -> None:
    company = create_company()
    before = len(outbox())

    def broken(session, event):
        raise RuntimeError("fallo simulado al escribir la outbox")

    with patch("operational_context_service.application.audit_events.record_audit_event", side_effect=broken):
        response = audited_api.put(f"/api/v1/companies/{company['id']}", json=update_body(company, timezone="America/Lima"))

    assert response.status_code == 500
    assert len(outbox()) == before
    current = audited_api.get(f"/api/v1/companies/{company['id']}").json()
    assert current["timezone"] == company["timezone"] and current["version"] == company["version"]


def test_database_rejection_at_commit_leaves_no_event(audited_api, create_company, fake_organizations, outbox) -> None:
    company = create_company()
    before = len(outbox())

    duplicated = audited_api.post("/api/v1/companies", json=company_payload(company["organization_identity_id"]))

    assert duplicated.status_code == 409
    assert len(outbox()) == before


@pytest.mark.parametrize("unused", [None])
def test_record_audit_event_is_the_library_function(unused) -> None:
    from operational_context_service.application import audit_events

    assert audit_events.record_audit_event is sio_outbox.record_audit_event
