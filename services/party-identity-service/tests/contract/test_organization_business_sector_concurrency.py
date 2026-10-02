"""Concurrencia del sector principal con 20 solicitudes (T060; RC-04, RC-18, SC-004)."""

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
                "SELECT count(*) FROM organization_business_sectors "
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


def _sectors(api, prefix: str) -> list[dict]:
    return [
        api.post(
            "/api/v1/global-business-sectors",
            json={"classification_system": "TEST", "code": f"{prefix}{i:02d}", "name": f"Sector {i}"},
        ).json()
        for i in range(CONCURRENT_REQUESTS)
    ]


def test_twenty_simultaneous_set_primary_leave_exactly_one(api, test_engine) -> None:
    organization = create_organization(api)
    url = f"/api/v1/organization-identities/{organization['id']}/business-sectors"
    assignments = [
        api.post(url, json={"global_business_sector_id": sector["id"], "is_primary": index == 0}).json()
        for index, sector in enumerate(_sectors(api, "S"))
    ]

    statuses = _parallel([
        (lambda assignment=assignment: api.post(
            f"/api/v1/organization-business-sectors/{assignment['id']}:set-primary",
            json={"version": assignment["version"]},
        ).status_code)
        for assignment in assignments
    ])

    assert set(statuses) <= {200, 409}
    assert _primaries(test_engine, organization["id"]) == 1


def test_twenty_simultaneous_primary_assignments_give_one_created(api, test_engine) -> None:
    organization = create_organization(api)
    url = f"/api/v1/organization-identities/{organization['id']}/business-sectors"
    sectors = _sectors(api, "P")

    responses = _parallel([
        (lambda sector=sector: api.post(url, json={"global_business_sector_id": sector["id"], "is_primary": True}))
        for sector in sectors
    ])

    statuses = [response.status_code for response in responses]
    assert statuses.count(201) == 1
    assert all(
        response.json()["code"] == "PARTY_IDENTITY.PRIMARY_SECTOR_CONFLICT"
        for response in responses
        if response.status_code != 201
    )
    assert _primaries(test_engine, organization["id"]) == 1
