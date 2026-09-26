"""Concurrencia de asesores (RC-04, RC-08, SC-007): nunca dos principales vigentes."""

from datetime import UTC, datetime, timedelta
import threading

from sqlalchemy import text

from tests.api.test_uniqueness_concurrency import _parallel


def _primaries(test_engine, company_id):
    with test_engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT count(*) FILTER (WHERE status = 'ACTIVE' AND is_primary), "
                "count(*) FILTER (WHERE status = 'INACTIVE') FROM company_advisor_assignments "
                "WHERE company_id = :c"
            ),
            {"c": company_id},
        ).one()


def test_two_primary_creations_in_parallel(api, create_company, fake_persons, test_engine):
    company = create_company()
    persons = iter([str(fake_persons.add()), str(fake_persons.add())])
    lock = threading.Lock()

    def create():
        with lock:
            person = next(persons)
        return api.post(
            f"/api/v1/companies/{company['id']}/advisor-assignments",
            json={"person_identity_id": person},
        )

    assert _parallel(create) == [201, 409]
    assert _primaries(test_engine, company["id"]) == (1, 0)


def test_two_changes_in_parallel_leave_exactly_one_primary(api, create_company, fake_persons, test_engine):
    company = create_company()
    current = api.post(
        f"/api/v1/companies/{company['id']}/advisor-assignments",
        json={
            "person_identity_id": str(fake_persons.add()),
            "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
    ).json()
    persons = iter([str(fake_persons.add()), str(fake_persons.add())])
    lock = threading.Lock()

    def change():
        with lock:
            person = next(persons)
        return api.post(
            f"/api/v1/companies/{company['id']}/advisor-assignments/change-primary",
            json={"current_assignment_id": current["id"], "version": current["version"], "person_identity_id": person},
        )

    statuses = _parallel(change)

    assert statuses[0] == 201 and statuses[1] == 409
    # Un principal vigente y la anterior cerrada una sola vez: sin cierre huérfano.
    assert _primaries(test_engine, company["id"]) == (1, 1)
