"""Rechazos sin evento, atomicidad y `seed` sin eventos en PI (feature 016; DS-02, RC-01, RC-06; T049)."""

from __future__ import annotations

from unittest.mock import patch

from tests.conftest import person_payload
from tests.phase_b import create_person


def test_rejections_record_no_event(api, api_as, anonymous, outbox) -> None:
    person = create_person(api)
    before = len(outbox())
    url = f"/api/v1/person-identities/{person['id']}"

    assert anonymous.post("/api/v1/person-identities", json=person_payload(identification_number="1000000900")).status_code == 401
    assert api_as("perm:party-identity:person_identities:read").post(f"{url}/deactivate", json={"version": 1}).status_code == 403
    assert api.post(f"{url}/deactivate", json={"version": 99}).status_code == 409
    invalid = person_payload(identification_number="1000000901")
    invalid.pop("first_name")
    assert api.post("/api/v1/person-identities", json=invalid).status_code == 422
    assert api.post("/api/v1/person-identities", json=person_payload(identification_number=person["identification_number"])).status_code == 409

    assert len(outbox()) == before


def test_failure_after_recording_rolls_back_change_and_event(api, outbox) -> None:
    person = create_person(api)
    before = len(outbox())

    with patch(
        "party_identity_service.application.audit_events.record_audit_event",
        side_effect=RuntimeError("fallo simulado al escribir la outbox"),
    ):
        response = api.post(f"/api/v1/person-identities/{person['id']}/deactivate", json={"version": person["version"]})

    assert response.status_code == 500
    assert len(outbox()) == before
    assert api.get(f"/api/v1/person-identities/{person['id']}").json()["status"] == "ACTIVE"


def test_seed_loading_records_no_event(session_factory, outbox) -> None:
    """La carga del catálogo CIIU por `seed` no es una acción de usuario: sin autor, sin evento."""
    from party_identity_service.infrastructure.business_sector_repository import (
        SectorSeedRow,
        SQLAlchemyBusinessSectorRepository,
    )

    before = len(outbox())
    with session_factory() as session:
        result = SQLAlchemyBusinessSectorRepository(session).upsert_catalog(
            classification_system="SEED_TEST",
            rows=[SectorSeedRow(code="S1", name="Sector de seed (ficticio)", parent_code=None)],
            actor_id="system:seed",
        )

    assert result.created == 1
    assert len(outbox()) == before
