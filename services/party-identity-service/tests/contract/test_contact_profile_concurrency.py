"""Concurrencia de perfiles (T043; RC-03, SC-004, FR-020).

Las solicitudes simultáneas pasan por la API completa (servicio, bloqueo del
propietario e índice parcial) con un cliente HTTP por hilo.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import text

from tests.phase_b import create_organization, profile_payload, profile_url

CONCURRENT_REQUESTS = 20


def _active_count(test_engine, organization_id: str) -> int:
    with test_engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT count(*) FROM organization_contact_profiles "
                "WHERE organization_identity_id = :id AND is_active"
            ),
            {"id": organization_id},
        ).scalar_one()


def _run(api, requests):
    barrier = Barrier(len(requests))

    def call(args):
        url, body = args
        barrier.wait()
        return api.post(url, json=body).status_code

    with ThreadPoolExecutor(max_workers=len(requests)) as executor:
        return list(executor.map(call, requests))


def test_two_simultaneous_first_versions_leave_exactly_one(api, test_engine) -> None:
    organization = create_organization(api)
    url = profile_url("organization", organization["id"])

    statuses = _run(api, [(url, profile_payload(phone=f"+57 300 000 000{i}")) for i in range(2)])

    assert sorted(statuses) == [201, 409]
    assert _active_count(test_engine, organization["id"]) == 1


def test_twenty_simultaneous_replacements_keep_one_active_version(api, test_engine) -> None:
    organization = create_organization(api)
    url = profile_url("organization", organization["id"])
    current = api.post(url, json=profile_payload()).json()

    statuses = _run(
        api,
        [
            (url, profile_payload(phone=f"+57 300 000 {i:04d}", version=current["version"]))
            for i in range(CONCURRENT_REQUESTS)
        ],
    )

    assert statuses.count(201) == 1
    assert set(statuses) <= {201, 409}
    assert _active_count(test_engine, organization["id"]) == 1


def test_two_simultaneous_closes_give_one_ok_and_one_already_closed(api, test_engine) -> None:
    organization = create_organization(api)
    url = profile_url("organization", organization["id"])
    current = api.post(url, json=profile_payload()).json()
    barrier = Barrier(2)

    def close(_):
        barrier.wait()
        response = api.post(f"{url}:close", json={"version": current["version"]})
        return response.status_code, response.json().get("code")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = sorted(executor.map(close, range(2)), key=lambda item: item[0])

    assert results[0][0] == 200
    assert results[1] == (409, "PARTY_IDENTITY.CONTACT_PROFILE_ALREADY_CLOSED")
    assert _active_count(test_engine, organization["id"]) == 0
    with test_engine.connect() as connection:
        closed = connection.execute(
            text("SELECT count(*) FROM organization_contact_profiles WHERE NOT is_active")
        ).scalar_one()
    assert closed == 1
