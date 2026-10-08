"""DS-06: datos personales sensibles nunca salen con su valor (feature 016; RC-05; SC-004; T048).

Recorre altas y modificaciones con valores sensibles conocidos y busca esos valores en todas las
filas de la outbox y en todos los logs capturados.
"""

from __future__ import annotations

import logging

from tests.conftest import person_payload
from tests.phase_b import create_organization, profile_payload, profile_url

SENSITIVE = {
    "identification_number": "1000000555",
    "birth_date": "1985-03-04",
    "email": "persona.sensible@correo-ficticio.co",
    "phone": "+57 300 555 0555",
    "address_line": "Carrera Sensible 55 # 55-55",
    "postal_code": "050055",
}


def test_sensitive_values_never_reach_outbox_or_logs(api, outbox, caplog) -> None:
    with caplog.at_level(logging.DEBUG):
        person = api.post("/api/v1/person-identities", json=person_payload(
            identification_number=SENSITIVE["identification_number"], birth_date=SENSITIVE["birth_date"],
        ))
        assert person.status_code == 201, person.text
        profile = api.post(profile_url("person", person.json()["id"]), json=profile_payload(
            email=SENSITIVE["email"], phone=SENSITIVE["phone"], address_line=SENSITIVE["address_line"],
            postal_code=SENSITIVE["postal_code"],
        ))
        assert profile.status_code == 201, profile.text
        organization = create_organization(api)
        contact = api.post(f"/api/v1/organization-identities/{organization['id']}/contact-persons", json={
            "person_identity_id": person.json()["id"], "position": "Cartera",
            "email": SENSITIVE["email"], "phone": SENSITIVE["phone"],
        })
        assert contact.status_code == 201, contact.text

    events = outbox()
    assert events
    serialized = repr(events)
    for field, value in SENSITIVE.items():
        assert value not in serialized, field
        assert value not in caplog.text, field
    for event in events:
        for side in ("previous_values", "new_values"):
            for field, value in (event[side] or {}).items():
                if field in SENSITIVE and value is not None:
                    assert value in ("<registrado>", "<modificado>", "<eliminado>")
                    assert f"{side}.{field}" in event["redacted_paths"]
    person_event = next(e for e in events if e["entity_type"] == "PersonIdentity")
    assert person_event["new_values"]["first_name"] == "ANA"  # los nombres sí van con su valor
