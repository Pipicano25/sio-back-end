"""Cambio de asesor principal (US5; FR-053; DS-13, DS-15, C-12; RC-08)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

SUPERVISOR = ("perm:all:all:read", "perm:all:all:create", "perm:all:all:update")


def _iso(delta: timedelta = timedelta()) -> str:
    return (datetime.now(UTC) + delta).isoformat()


@pytest.fixture
def primary(api, create_company, fake_persons):
    company = create_company()
    current = api.post(
        f"/api/v1/companies/{company['id']}/advisor-assignments",
        json={"person_identity_id": str(fake_persons.add()), "valid_from": _iso(timedelta(days=-30))},
    ).json()
    fake_persons.reset()
    return company, current


def _change(client, company, current, person, **extra):
    body = {
        "current_assignment_id": current["id"],
        "version": current["version"],
        "person_identity_id": str(person),
        **extra,
    }
    return client.post(f"/api/v1/companies/{company['id']}/advisor-assignments/change-primary", json=body)


def _rows(test_engine, company_id):
    with test_engine.connect() as connection:
        return connection.execute(
            text("SELECT status, is_primary FROM company_advisor_assignments WHERE company_id = :c"),
            {"c": company_id},
        ).all()


def test_change_closes_current_and_creates_new(api, primary, fake_persons):
    company, current = primary
    new_person = fake_persons.add()

    response = _change(api, company, current, new_person)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["closed"]["id"] == current["id"]
    assert body["closed"]["status"] == "INACTIVE"
    assert body["closed"]["person_identity_id"] == current["person_identity_id"]
    assert body["created"]["status"] == "ACTIVE" and body["created"]["is_primary"] is True
    assert body["created"]["person_identity_id"] == str(new_person)
    assert body["closed"]["valid_to"] == body["created"]["valid_from"]
    assert fake_persons.count("get_person") == 1


@pytest.mark.parametrize(
    ("status", "code", "http"),
    [(None, "PERSON_IDENTITY_NOT_FOUND", 422), ("INACTIVE", "PERSON_IDENTITY_INACTIVE", 422), ("down", "DEPENDENCY_UNAVAILABLE", 503)],
)
def test_new_person_is_validated_before_writing(api, primary, fake_persons, test_engine, status, code, http):
    company, current = primary
    if status == "down":
        person = fake_persons.add()
        fake_persons.mode = "unavailable"
    else:
        person = fake_persons.add(status) if status else "00000000-0000-4000-8000-00000000cafe"

    response = _change(api, company, current, person)

    assert response.status_code == http
    assert response.json()["code"] == f"OPERATIONAL_CONTEXT.{code}"
    assert _rows(test_engine, company["id"]) == [("ACTIVE", True)]


def test_without_primary_is_409(api, primary, fake_persons):
    company, current = primary
    api.post(f"/api/v1/advisor-assignments/{current['id']}/close", json={"version": 1})

    response = _change(api, company, {**current, "version": 2}, fake_persons.add())

    assert response.json()["code"] == "OPERATIONAL_CONTEXT.NO_ACTIVE_PRIMARY_ADVISOR"


def test_current_that_is_not_the_primary_is_409(api, primary, fake_persons):
    company, _ = primary
    helper = api.post(
        f"/api/v1/companies/{company['id']}/advisor-assignments",
        json={"person_identity_id": str(fake_persons.add()), "is_primary": False},
    ).json()

    response = _change(api, company, helper, fake_persons.add())

    assert response.json()["code"] == "OPERATIONAL_CONTEXT.PRIMARY_ADVISOR_MISMATCH"


def test_person_already_non_primary_advisor_is_409(api, primary, fake_persons):
    company, current = primary
    person = fake_persons.add()
    api.post(
        f"/api/v1/companies/{company['id']}/advisor-assignments",
        json={"person_identity_id": str(person), "is_primary": False},
    )

    response = _change(api, company, current, person)

    assert response.json()["code"] == "OPERATIONAL_CONTEXT.DUPLICATE_ADVISOR_ASSIGNMENT"


def test_stale_version_and_invalid_effective_at(api, primary, fake_persons):
    company, current = primary

    stale = _change(api, company, {**current, "version": 5}, fake_persons.add())
    future = _change(api, company, current, fake_persons.add(), effective_at=_iso(timedelta(days=1)))
    before_start = _change(api, company, current, fake_persons.add(), effective_at=_iso(timedelta(days=-60)))

    assert stale.json()["code"] == "OPERATIONAL_CONTEXT.VERSION_CONFLICT"
    assert future.json()["code"] == "OPERATIONAL_CONTEXT.INVALID_VALIDITY_PERIOD"
    assert before_start.json()["code"] == "OPERATIONAL_CONTEXT.INVALID_VALIDITY_PERIOD"


def test_requires_create_and_delete(api_as, primary, make_member, fake_persons):
    company, current = primary
    make_member(company["id"], "supervisor.test")
    supervisor = api_as(*SUPERVISOR, sub="supervisor.test")

    response = _change(supervisor, company, current, fake_persons.add())

    assert response.status_code == 403
