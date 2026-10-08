"""Eventos de perfiles y personas de contacto (feature 016; acciones PI 13–21; DS-06, DS-11; T046).

Cada versión nueva del perfil es un evento de plataforma sobre la versión nueva, con la versión
cerrada en `previous_values`; el actor es el usuario que confirmó (`application_user_id`) y la
empresa confirmante va como dato de negocio. Correo, teléfono, dirección y código postal: marcador.
"""

from __future__ import annotations

from tests.conftest import COMPANY_ID
from tests.contract.test_audit_events_identities import check
from tests.phase_b import create_organization, create_person, profile_payload, profile_url

PROTECTED_VALUES = ("contacto@ejemplo-ficticio.co", "+57 601 555 0100", "Calle 00 # 00-00 (ficticia)", "110111")


def test_person_contact_profile_versions_and_close(api, fake_membership, outbox, clear_outbox) -> None:
    person = create_person(api)
    url = profile_url("person", person["id"])
    clear_outbox()
    first = api.post(url, json=profile_payload())
    assert first.status_code == 201, first.text
    same = api.post(url, json=profile_payload(version=first.json()["version"]))
    assert same.status_code == 200  # sin cambios: sin versión nueva y sin evento
    second = api.post(url, json=profile_payload(phone="+57 601 555 0199", version=first.json()["version"]))
    assert second.status_code == 201, second.text
    closed = api.post(f"{url}:close", json={"version": second.json()["version"]})
    assert closed.status_code == 200, closed.text

    register_first, register_second, close = outbox()
    confirmer = str(fake_membership.application_user_id(COMPANY_ID, "user-admin"))
    check(register_first, "REGISTER_PERSON_CONTACT_PROFILE", "PersonContactProfile", first.json()["id"])
    assert register_first["application_user_id"] == confirmer
    assert register_first["new_values"]["confirmed_by_company_id"] == str(COMPANY_ID)
    assert register_first["new_values"]["person_identity_id"] == person["id"]
    for field in ("email", "phone", "address_line", "postal_code"):
        assert register_first["new_values"][field] == "<registrado>"
        assert f"new_values.{field}" in register_first["redacted_paths"]
    assert register_first["new_values"]["city_id"] == profile_payload()["city_id"]

    check(register_second, "REGISTER_PERSON_CONTACT_PROFILE", "PersonContactProfile", second.json()["id"])
    assert register_second["previous_values"]["previous_profile_id"] == first.json()["id"]
    assert register_second["previous_values"]["phone"] == "<modificado>"
    assert register_second["new_values"]["phone"] == "<modificado>"

    check(close, "CLOSE_PERSON_CONTACT_PROFILE", "PersonContactProfile", second.json()["id"])
    assert close["previous_values"]["is_active"] is True and close["new_values"]["is_active"] is False
    for event in (register_first, register_second, close):
        assert not any(value in repr(event) for value in PROTECTED_VALUES) and "+57 601 555 0199" not in repr(event)


def test_organization_contact_profile_register_and_close(api, outbox, clear_outbox) -> None:
    organization = create_organization(api)
    url = profile_url("organization", organization["id"])
    clear_outbox()
    created = api.post(url, json=profile_payload())
    assert created.status_code == 201, created.text
    assert api.post(f"{url}:close", json={"version": created.json()["version"]}).status_code == 200

    register, close = outbox()
    check(register, "REGISTER_ORGANIZATION_CONTACT_PROFILE", "OrganizationContactProfile", created.json()["id"])
    check(close, "CLOSE_ORGANIZATION_CONTACT_PROFILE", "OrganizationContactProfile", created.json()["id"])


def test_contact_person_lifecycle(api, outbox, clear_outbox) -> None:
    organization = create_organization(api)
    base = f"/api/v1/organization-identities/{organization['id']}/contact-persons"
    clear_outbox()
    first = api.post(base, json={"person_identity_id": create_person(api)["id"], "position": "Cartera",
                                 "email": "cartera@ejemplo-ficticio.co", "is_primary": True})
    assert first.status_code == 201, first.text
    second = api.post(base, json={"person_identity_id": create_person(api, number="1000000002")["id"], "position": "Ventas"})
    assert second.status_code == 201, second.text
    contact = second.json()
    url = f"/api/v1/organization-contact-persons/{contact['id']}"
    updated = api.put(url, json={"position": "Logística", "phone": "+57 601 555 0101", "version": contact["version"]})
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    primary = api.post(f"{url}:set-primary", json={"version": version})
    assert primary.status_code == 200, primary.text
    version = primary.json()["version"]
    assert api.post(f"{url}:deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{url}:reactivate", json={"version": version + 1}).status_code == 200

    events = [e for e in outbox() if e["entity_type"] == "OrganizationContactPerson"]
    assert [e["action"] for e in events] == [
        "CREATE_ORGANIZATION_CONTACT_PERSON", "CREATE_ORGANIZATION_CONTACT_PERSON", "UPDATE_ORGANIZATION_CONTACT_PERSON",
        "SET_PRIMARY_ORGANIZATION_CONTACT_PERSON", "DEACTIVATE_ORGANIZATION_CONTACT_PERSON", "REACTIVATE_ORGANIZATION_CONTACT_PERSON",
    ]
    assert events[0]["new_values"]["email"] == "<registrado>" and "cartera@ejemplo-ficticio.co" not in repr(events[0])
    assert events[2]["previous_values"]["position"] == "Ventas" and events[2]["new_values"]["position"] == "Logística"
    assert events[2]["new_values"]["phone"] == "<registrado>"
    assert events[3]["previous_values"]["previous_primary_id"] == first.json()["id"]
    assert events[3]["new_values"]["is_primary"] is True
