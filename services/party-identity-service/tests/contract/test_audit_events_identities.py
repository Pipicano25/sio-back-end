"""Eventos de personas, organizaciones y reglas (feature 016; acciones PI 1–12; DS-06; T045).

Eventos de plataforma (`company_id` nulo). Número de identificación y fecha de nacimiento solo como
marcador y en `redacted_paths`; los nombres con su valor.
"""

from __future__ import annotations

from tests.conftest import rule_payload
from tests.phase_b import create_organization, create_person

R = "/api/v1/identification-type-rules"


def check(event: dict, action: str, entity_type: str, entity_id: str) -> None:
    assert event["action"] == action and event["entity_type"] == entity_type
    assert event["entity_id"] == entity_id and event["result"] == "SUCCESS"
    assert event["company_id"] is None and event["branch_id"] is None


def test_person_lifecycle_with_protected_fields(api, outbox, clear_outbox) -> None:
    clear_outbox()
    person = create_person(api, number="1000000077")
    url = f"/api/v1/person-identities/{person['id']}"
    body = {key: person[key] for key in (
        "identification_country_id", "identification_type", "identification_number", "first_name",
        "middle_name", "last_name", "second_last_name", "birth_date", "verification_status", "version",
    )}
    renamed = api.put(url, json={**body, "first_name": "BEATRIZ"})
    assert renamed.status_code == 200, renamed.text
    version = renamed.json()["version"]
    renumbered = api.put(url, json={**body, "first_name": "BEATRIZ", "identification_number": "1000000078", "version": version})
    assert renumbered.status_code == 200, renumbered.text
    version = renumbered.json()["version"]
    assert api.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    create, rename, renumber, deactivate, reactivate = outbox()
    check(create, "CREATE_PERSON_IDENTITY", "PersonIdentity", person["id"])
    assert create["new_values"]["first_name"] == person["first_name"]
    assert create["new_values"]["identification_number"] == "<registrado>"
    assert "new_values.identification_number" in create["redacted_paths"]
    assert rename["action"] == "UPDATE_PERSON_IDENTITY"
    assert rename["previous_values"] == {"first_name": person["first_name"]} and rename["new_values"] == {"first_name": "BEATRIZ"}
    assert renumber["previous_values"] == {"identification_number": "<modificado>"}
    assert renumber["new_values"] == {"identification_number": "<modificado>"}
    assert sorted(renumber["redacted_paths"]) == ["new_values.identification_number", "previous_values.identification_number"]
    assert deactivate["action"] == "DEACTIVATE_PERSON_IDENTITY" and reactivate["action"] == "REACTIVATE_PERSON_IDENTITY"
    for event in outbox():
        assert "1000000077" not in repr(event) and "1000000078" not in repr(event)


def test_organization_lifecycle(api, outbox, clear_outbox) -> None:
    clear_outbox()
    organization = create_organization(api, number="900000077-1")
    url = f"/api/v1/organization-identities/{organization['id']}"
    body = {key: organization[key] for key in ("country_id", "identification_type", "identification_number", "legal_name", "version")}
    for optional in ("trade_name", "verification_status"):
        if optional in organization:
            body[optional] = organization[optional]
    updated = api.put(url, json={**body, "legal_name": "ORGANIZACION RENOMBRADA S.A.S."})
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert api.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    create, update, deactivate, reactivate = outbox()
    check(create, "CREATE_ORGANIZATION_IDENTITY", "OrganizationIdentity", organization["id"])
    assert create["new_values"]["legal_name"] == organization["legal_name"]
    assert create["new_values"]["identification_number"] == "<registrado>"
    assert "900000077" not in repr(create)
    assert update["new_values"] == {"legal_name": "ORGANIZACION RENOMBRADA S.A.S."}
    assert [deactivate["action"], reactivate["action"]] == ["DEACTIVATE_ORGANIZATION_IDENTITY", "REACTIVATE_ORGANIZATION_IDENTITY"]


def test_identification_rule_create_update_version_and_deactivate(api, outbox, clear_outbox) -> None:
    clear_outbox()
    created = api.post(R, json=rule_payload(identification_type="AUDIT_TEST_ID", sigla="AT", number_pattern="^[0-9]{6}$",
                                            example_value="123456"))
    assert created.status_code == 201, created.text
    rule = created.json()
    updated = api.put(f"{R}/{rule['id']}", json={
        "number_pattern_description": "Seis dígitos (ficticio).", "example_value": rule["example_value"], "version": rule["version"],
    })
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    successor = api.post(f"{R}/{rule['id']}/versions", json={
        "number_pattern": "^[0-9]{7}$", "number_pattern_description": "Siete dígitos (ficticio).", "version": version,
    })
    assert successor.status_code == 201, successor.text
    new_rule = successor.json()
    retired = api.post(f"{R}/{new_rule['id']}/deactivate", json={"version": new_rule["version"]})
    assert retired.status_code == 200, retired.text

    create, update, version_event, deactivate = outbox()
    check(create, "CREATE_IDENTIFICATION_TYPE_RULE", "IdentificationTypeRule", rule["id"])
    check(update, "UPDATE_IDENTIFICATION_TYPE_RULE", "IdentificationTypeRule", rule["id"])
    assert update["new_values"] == {"number_pattern_description": "Seis dígitos (ficticio)."}
    check(version_event, "CREATE_IDENTIFICATION_TYPE_RULE_VERSION", "IdentificationTypeRule", new_rule["id"])
    assert version_event["previous_values"]["previous_version_id"] == rule["id"]
    assert version_event["new_values"]["number_pattern"] == "^[0-9]{7}$"
    check(deactivate, "DEACTIVATE_IDENTIFICATION_TYPE_RULE", "IdentificationTypeRule", new_rule["id"])
    assert deactivate["new_values"]["is_active"] is False
