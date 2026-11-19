"""`PUT` parcial y versión opcional (constitución 4.0.0: Principio VII, D9, D10 y D28).

- El `PUT` recibe solo los campos que cambian; un campo ausente no cambia.
- `null` borra un campo opcional; en un campo obligatorio responde `422`.
- Un cuerpo vacío o solo con `version` responde `422`.
- `version` es opcional: si llega y no coincide, `409`; si no llega, gana la última escritura.
- Inactivar, reactivar y cerrar no exigen versión ni cuerpo.
"""

from __future__ import annotations

import pytest

from tests.conftest import organization_payload, person_payload, rule_payload
from tests.phase_b import code, create_organization, create_person

ORGS = "/api/v1/organization-identities"
PEOPLE = "/api/v1/person-identities"
SECTORS = "/api/v1/global-business-sectors"
RULES = "/api/v1/identification-type-rules"


@pytest.fixture
def organization(api):
    response = api.post(ORGS, json=organization_payload(trade_name="NOMBRE COMERCIAL", website="https://dao.com.co"))
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------- organizaciones


def test_put_with_one_field_changes_only_that_field(api, organization) -> None:
    response = api.put(f"{ORGS}/{organization['id']}", json={"trade_name": "Droguerías Alianza de Occidente - DAO"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["trade_name"] == "Droguerías Alianza de Occidente - DAO"
    for field in ("legal_name", "identification_number", "country_id", "website"):
        assert body[field] == organization[field]
    assert body["version"] == organization["version"] + 1


def test_put_without_version_applies_over_current(api, organization) -> None:
    api.put(f"{ORGS}/{organization['id']}", json={"trade_name": "PRIMERO"})

    response = api.put(f"{ORGS}/{organization['id']}", json={"trade_name": "SEGUNDO"})

    assert response.status_code == 200, response.text
    assert response.json()["trade_name"] == "SEGUNDO"
    assert response.json()["version"] == organization["version"] + 2


def test_put_with_stale_version_is_conflict(api, organization) -> None:
    api.put(f"{ORGS}/{organization['id']}", json={"trade_name": "PRIMERO"})

    response = api.put(f"{ORGS}/{organization['id']}", json={"trade_name": "SEGUNDO", "version": organization["version"]})

    assert response.status_code == 409
    assert code(response) == "VERSION_CONFLICT"
    assert api.get(f"{ORGS}/{organization['id']}").json()["trade_name"] == "PRIMERO"


def test_put_with_current_version_is_accepted(api, organization) -> None:
    response = api.put(f"{ORGS}/{organization['id']}", json={"trade_name": "OTRO", "version": organization["version"]})

    assert response.status_code == 200, response.text


def test_null_clears_an_optional_field(api, organization) -> None:
    response = api.put(f"{ORGS}/{organization['id']}", json={"website": None})

    assert response.status_code == 200, response.text
    assert response.json()["website"] is None
    assert response.json()["trade_name"] == "NOMBRE COMERCIAL"


@pytest.mark.parametrize("field", ["legal_name", "identification_number", "identification_type", "country_id"])
def test_null_in_a_required_field_is_rejected(api, organization, field) -> None:
    response = api.put(f"{ORGS}/{organization['id']}", json={field: None})

    assert response.status_code == 422
    assert api.get(f"{ORGS}/{organization['id']}").json()["version"] == organization["version"]


@pytest.mark.parametrize("body", [{}, {"version": 1}])
def test_body_without_fields_to_change_is_rejected(api, organization, body) -> None:
    response = api.put(f"{ORGS}/{organization['id']}", json=body)

    assert response.status_code == 422


def test_unknown_field_is_rejected(api, organization) -> None:
    response = api.put(f"{ORGS}/{organization['id']}", json={"nombre": "X"})

    assert response.status_code == 422


def test_same_value_does_not_write(api, organization) -> None:
    response = api.put(f"{ORGS}/{organization['id']}", json={"legal_name": organization["legal_name"]})

    assert response.status_code == 200
    assert response.json()["version"] == organization["version"]


def test_changing_only_the_number_is_validated_with_the_stored_sigla(api, organization) -> None:
    bad = api.put(f"{ORGS}/{organization['id']}", json={"identification_number": "817004260-5"})
    good = api.put(f"{ORGS}/{organization['id']}", json={"identification_number": "817004260-0"})

    assert bad.status_code == 422
    assert code(bad) == "INVALID_IDENTIFICATION_NUMBER"
    assert good.status_code == 200, good.text
    assert good.json()["identification_type"] == "NIT"


def test_status_actions_work_without_body_and_with_empty_body(api, organization) -> None:
    deactivated = api.post(f"{ORGS}/{organization['id']}/deactivate")
    reactivated = api.post(f"{ORGS}/{organization['id']}/reactivate", json={})

    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "INACTIVE"
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["status"] == "ACTIVE"


def test_status_action_with_stale_version_is_conflict(api, organization) -> None:
    api.put(f"{ORGS}/{organization['id']}", json={"trade_name": "OTRO"})

    response = api.post(f"{ORGS}/{organization['id']}/deactivate", json={"version": organization["version"]})

    assert response.status_code == 409
    assert api.get(f"{ORGS}/{organization['id']}").json()["status"] == "ACTIVE"


# ---------------------------------------------------------------- personas


def test_person_put_changes_one_name_and_keeps_the_rest(api) -> None:
    person = api.post(PEOPLE, json=person_payload(middle_name="ANDRES")).json()

    response = api.put(f"{PEOPLE}/{person['id']}", json={"second_last_name": "PEREZ"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["second_last_name"] == "PEREZ"
    assert body["middle_name"] == "ANDRES"
    assert body["first_name"] == person["first_name"]
    assert body["identification_number"] == person["identification_number"]


def test_person_null_clears_middle_name_and_rejects_null_first_name(api) -> None:
    person = api.post(PEOPLE, json=person_payload(middle_name="ANDRES")).json()

    cleared = api.put(f"{PEOPLE}/{person['id']}", json={"middle_name": None})
    rejected = api.put(f"{PEOPLE}/{person['id']}", json={"first_name": None})

    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["middle_name"] is None
    assert rejected.status_code == 422


def test_person_status_actions_without_version(api) -> None:
    person = create_person(api)

    assert api.post(f"{PEOPLE}/{person['id']}/deactivate").json()["status"] == "INACTIVE"
    assert api.post(f"{PEOPLE}/{person['id']}/reactivate").json()["status"] == "ACTIVE"


# ---------------------------------------------------------------- otros recursos


def test_business_sector_put_changes_only_description(api) -> None:
    sector = api.post(
        SECTORS, json={"classification_system": "test_system", "code": "P1", "name": "Sector P1"}
    ).json()

    response = api.put(f"{SECTORS}/{sector['id']}", json={"description": "Descripción nueva"})

    assert response.status_code == 200, response.text
    assert response.json()["description"] == "Descripción nueva"
    assert response.json()["name"] == "Sector P1"
    assert api.post(f"{SECTORS}/{sector['id']}:deactivate").json()["status"] == "INACTIVE"


def test_contact_person_put_changes_only_email(api) -> None:
    organization = create_organization(api)
    contact = api.post(
        f"{ORGS}/{organization['id']}/contact-persons", json={"position": "Compras", "phone": "+57 601 555 0101"}
    ).json()

    response = api.put(f"/api/v1/organization-contact-persons/{contact['id']}", json={"email": "compras@dao.com.co"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "compras@dao.com.co"
    assert body["phone"] == "+57 601 555 0101" and body["position"] == "Compras"
    assert api.post(f"/api/v1/organization-contact-persons/{contact['id']}:deactivate").status_code == 200


def test_legal_representative_put_changes_only_position(api) -> None:
    organization = create_organization(api)
    person = create_person(api)
    representative = api.post(
        f"{ORGS}/{organization['id']}/legal-representatives",
        json={"person_identity_id": person["id"], "representative_type": "OTHER", "position": "Suplente",
              "source_document_reference": "ACTA-1"},
    ).json()

    response = api.put(
        f"/api/v1/organization-legal-representatives/{representative['id']}", json={"position": "Gerente suplente"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["position"] == "Gerente suplente"
    assert response.json()["source_document_reference"] == "ACTA-1"
    closed = api.post(f"/api/v1/organization-legal-representatives/{representative['id']}:close")
    assert closed.status_code == 200, closed.text


@pytest.mark.empty_rules
def test_rule_put_changes_only_example(api) -> None:
    rule = api.post(RULES, json=rule_payload()).json()

    response = api.put(f"{RULES}/{rule['id']}", json={"example_value": rule["example_value"]})
    description = api.put(f"{RULES}/{rule['id']}", json={"number_pattern_description": "Descripción nueva"})

    assert response.status_code == 200, response.text
    assert description.status_code == 200, description.text
    assert description.json()["number_pattern_description"] == "Descripción nueva"
    assert description.json()["example_value"] == rule["example_value"]
    assert api.post(f"{RULES}/{rule['id']}/deactivate").status_code == 200
