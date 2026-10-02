"""Concurrencia del representante PRIMARY con 20 solicitudes (T071; RC-04, RC-18, SC-004)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import text

from tests.phase_b import create_organization, create_person

CONCURRENT_REQUESTS = 20


def _primaries(test_engine, organization_id: str) -> int:
    with test_engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT count(*) FROM organization_legal_representatives "
                "WHERE organization_identity_id = :id AND is_active AND representative_type = 'PRIMARY'"
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


@pytest.mark.parametrize("with_previous_primary", [False, True])
def test_twenty_simultaneous_set_primary_leave_exactly_one(api, test_engine, with_previous_primary) -> None:
    organization = create_organization(api)
    url = f"/api/v1/organization-identities/{organization['id']}/legal-representatives"
    persons = [create_person(api, number=f"10000001{i:02d}") for i in range(CONCURRENT_REQUESTS)]
    current_version = None
    if with_previous_primary:
        previous = create_person(api, number="1000000999")
        current_version = api.post(
            url, json={"person_identity_id": previous["id"], "representative_type": "PRIMARY"}
        ).json()["version"]

    responses = _parallel([
        (lambda person=person: api.post(
            f"{url}:set-primary",
            json={"person_identity_id": person["id"], "current_primary_version": current_version},
        ))
        for person in persons
    ])

    statuses = [response.status_code for response in responses]
    assert statuses.count(201) >= 1
    assert set(statuses) <= {201, 409}
    assert _primaries(test_engine, organization["id"]) == 1


def test_twenty_simultaneous_primary_registrations_give_one_created(api, test_engine) -> None:
    organization = create_organization(api)
    url = f"/api/v1/organization-identities/{organization['id']}/legal-representatives"
    persons = [create_person(api, number=f"10000002{i:02d}") for i in range(CONCURRENT_REQUESTS)]

    responses = _parallel([
        (lambda person=person: api.post(url, json={"person_identity_id": person["id"], "representative_type": "PRIMARY"}))
        for person in persons
    ])

    statuses = [response.status_code for response in responses]
    assert statuses.count(201) == 1
    assert all(
        response.json()["code"] == "PARTY_IDENTITY.PRIMARY_REPRESENTATIVE_CONFLICT"
        for response in responses
        if response.status_code != 201
    )
    assert _primaries(test_engine, organization["id"]) == 1
