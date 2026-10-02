"""Concurrencia del contacto principal con 20 solicitudes (T053; RC-04, RC-18, SC-004)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import text

from tests.phase_b import create_organization

CONCURRENT_REQUESTS = 20


def _primaries(test_engine, organization_id: str) -> int:
    with test_engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT count(*) FROM organization_contact_persons "
                "WHERE organization_identity_id = :id AND is_active AND is_primary"
            ),
            {"id": organization_id},
        ).scalar_one()


def _parallel(calls):
    barrier = Barrier(len(calls))

    def run(call):
        barrier.wait()
        return call()

    with ThreadPoolExecutor(max_workers=len(calls)) as executor:
        return list(executor.map(run, calls))


def test_twenty_simultaneous_set_primary_leave_exactly_one_primary(api, test_engine) -> None:
    organization = create_organization(api)
    url = f"/api/v1/organization-identities/{organization['id']}/contact-persons"
    contacts = [
        api.post(url, json={"phone": f"+57 601 555 {i:04d}", "is_primary": i == 0}).json()
        for i in range(CONCURRENT_REQUESTS)
    ]

    statuses = _parallel([
        (lambda contact=contact: api.post(
            f"/api/v1/organization-contact-persons/{contact['id']}:set-primary",
            json={"version": contact["version"]},
        ).status_code)
        for contact in contacts
    ])

    assert set(statuses) <= {200, 409}
    assert _primaries(test_engine, organization["id"]) == 1


def test_twenty_simultaneous_primary_creations_give_one_created(api, test_engine) -> None:
    organization = create_organization(api)
    url = f"/api/v1/organization-identities/{organization['id']}/contact-persons"

    responses = _parallel([
        (lambda i=i: api.post(url, json={"phone": f"+57 601 556 {i:04d}", "is_primary": True}))
        for i in range(CONCURRENT_REQUESTS)
    ])

    statuses = [response.status_code for response in responses]
    assert statuses.count(201) == 1
    assert all(
        response.json()["code"] == "PARTY_IDENTITY.PRIMARY_CONTACT_CONFLICT"
        for response in responses
        if response.status_code != 201
    )
    assert _primaries(test_engine, organization["id"]) == 1
