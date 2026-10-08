"""Eventos de sectores y representantes legales (feature 016; acciones PI 22–32; T047)."""

from __future__ import annotations

from tests.contract.test_audit_events_identities import check
from tests.phase_b import create_organization, create_person

S = "/api/v1/global-business-sectors"


def _sector(api, code_value: str) -> dict:
    response = api.post(S, json={"classification_system": "TEST", "code": code_value, "name": f"Sector {code_value}"})
    assert response.status_code == 201, response.text
    return response.json()


def test_global_sector_lifecycle(api, outbox, clear_outbox) -> None:
    clear_outbox()
    sector = _sector(api, "A1")
    url = f"{S}/{sector['id']}"
    updated = api.put(url, json={"name": "Sector renombrado", "description": None, "version": sector["version"]})
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert api.post(f"{url}:deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{url}:reactivate", json={"version": version + 1}).status_code == 200

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_GLOBAL_BUSINESS_SECTOR", "UPDATE_GLOBAL_BUSINESS_SECTOR",
        "DEACTIVATE_GLOBAL_BUSINESS_SECTOR", "REACTIVATE_GLOBAL_BUSINESS_SECTOR",
    ]
    for event in events:
        check(event, event["action"], "GlobalBusinessSector", sector["id"])
    assert events[1]["new_values"]["name"] == "Sector renombrado"


def test_organization_sector_assign_set_primary_and_close(api, outbox, clear_outbox) -> None:
    organization = create_organization(api)
    first_sector, second_sector = _sector(api, "01"), _sector(api, "02")
    base = f"/api/v1/organization-identities/{organization['id']}/business-sectors"
    clear_outbox()
    first = api.post(base, json={"global_business_sector_id": first_sector["id"], "is_primary": True})
    assert first.status_code == 201, first.text
    second = api.post(base, json={"global_business_sector_id": second_sector["id"]})
    assert second.status_code == 201, second.text
    primary = api.post(f"/api/v1/organization-business-sectors/{second.json()['id']}:set-primary",
                       json={"version": second.json()["version"]})
    assert primary.status_code == 200, primary.text
    closed = api.post(f"/api/v1/organization-business-sectors/{first.json()['id']}:close",
                      json={"version": api.get(f"/api/v1/organization-business-sectors/{first.json()['id']}").json()["version"]})
    assert closed.status_code == 200, closed.text

    assign_first, assign_second, set_primary, close = outbox()
    check(assign_first, "ASSIGN_ORGANIZATION_BUSINESS_SECTOR", "OrganizationBusinessSector", first.json()["id"])
    check(assign_second, "ASSIGN_ORGANIZATION_BUSINESS_SECTOR", "OrganizationBusinessSector", second.json()["id"])
    check(set_primary, "SET_PRIMARY_ORGANIZATION_BUSINESS_SECTOR", "OrganizationBusinessSector", second.json()["id"])
    assert set_primary["previous_values"]["previous_primary_id"] == first.json()["id"]
    check(close, "CLOSE_ORGANIZATION_BUSINESS_SECTOR", "OrganizationBusinessSector", first.json()["id"])
    assert close["new_values"]["is_active"] is False


def test_legal_representative_lifecycle(api, outbox, clear_outbox) -> None:
    organization = create_organization(api)
    url = f"/api/v1/organization-identities/{organization['id']}/legal-representatives"
    clear_outbox()
    current = api.post(url, json={"person_identity_id": create_person(api)["id"], "representative_type": "PRIMARY",
                                  "position": "Gerente", "source_document_reference": "Acta 1 (ficticia)"})
    assert current.status_code == 201, current.text
    rep = current.json()
    updated = api.put(f"/api/v1/organization-legal-representatives/{rep['id']}", json={
        "position": "Presidente", "source_document_reference": "Acta 12 (ficticia)", "version": rep["version"],
    })
    assert updated.status_code == 200, updated.text
    successor = api.post(f"{url}:set-primary", json={
        "person_identity_id": create_person(api, number="1000000002")["id"], "current_primary_version": updated.json()["version"],
    })
    assert successor.status_code == 201, successor.text
    new_rep = successor.json()
    closed = api.post(f"/api/v1/organization-legal-representatives/{new_rep['id']}:close", json={"version": new_rep["version"]})
    assert closed.status_code == 200, closed.text

    events = [e for e in outbox() if e["entity_type"] == "OrganizationLegalRepresentative"]
    create, update, set_primary, close = events
    check(create, "CREATE_ORGANIZATION_LEGAL_REPRESENTATIVE", "OrganizationLegalRepresentative", rep["id"])
    assert create["new_values"]["source_document_reference"] == "<registrado>"
    check(update, "UPDATE_ORGANIZATION_LEGAL_REPRESENTATIVE", "OrganizationLegalRepresentative", rep["id"])
    assert update["new_values"]["position"] == "Presidente"
    assert update["new_values"]["source_document_reference"] == "<modificado>"
    check(set_primary, "SET_PRIMARY_ORGANIZATION_LEGAL_REPRESENTATIVE", "OrganizationLegalRepresentative", new_rep["id"])
    assert set_primary["previous_values"]["previous_primary_id"] == rep["id"]
    check(close, "CLOSE_ORGANIZATION_LEGAL_REPRESENTATIVE", "OrganizationLegalRepresentative", new_rep["id"])
    assert "Acta 1 (ficticia)" not in repr(events) and "Acta 12 (ficticia)" not in repr(events)
