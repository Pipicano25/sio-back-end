"""Asesores de empresa (US5; FR-050 a FR-058; DS-13, DS-15; RC-04, RC-05, RC-10)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text


def _iso(delta: timedelta = timedelta()) -> str:
    return (datetime.now(UTC) + delta).isoformat()


@pytest.fixture
def company(create_company):
    return create_company()


def _url(company_id):
    return f"/api/v1/companies/{company_id}/advisor-assignments"


def _create(api, company_id, person, **extra):
    return api.post(_url(company_id), json={"person_identity_id": str(person), **extra})


def test_create_primary_advisor(api, company, fake_persons):
    person = fake_persons.add()

    response = _create(api, company["id"], person)

    assert response.status_code == 201, response.text
    body = response.json()
    assert response.headers["Location"] == f"/api/v1/advisor-assignments/{body['id']}"
    assert body["is_primary"] is True and body["status"] == "ACTIVE"
    assert body["valid_to"] is None
    assert body["assigned_by"] == "user-admin"
    for personal in ("first_name", "last_name", "full_name", "email", "phone"):
        assert personal not in body


@pytest.mark.parametrize(
    ("status", "code"),
    [(None, "PERSON_IDENTITY_NOT_FOUND"), ("INACTIVE", "PERSON_IDENTITY_INACTIVE")],
)
def test_person_not_found_or_inactive(api, company, fake_persons, test_engine, status, code):
    person = fake_persons.add(status) if status else "00000000-0000-4000-8000-00000000beef"

    response = _create(api, company["id"], person)

    assert response.status_code == 422
    assert response.json()["code"] == f"OPERATIONAL_CONTEXT.{code}"
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM company_advisor_assignments")).scalar_one() == 0


def test_party_identity_unavailable(api, company, fake_persons):
    person = fake_persons.add()
    fake_persons.mode = "unavailable"

    response = _create(api, company["id"], person)

    assert response.status_code == 503
    assert response.json()["dependency"] == "party-identity"


def test_second_primary_and_same_person_are_409(api, create_company, company, fake_persons):
    person = fake_persons.add()
    _create(api, company["id"], person)

    second_primary = _create(api, company["id"], fake_persons.add())
    same_person = _create(api, company["id"], person, is_primary=False)
    non_primary = _create(api, company["id"], fake_persons.add(), is_primary=False)
    other_company = _create(api, create_company()["id"], person)

    assert second_primary.json()["code"] == "OPERATIONAL_CONTEXT.PRIMARY_ADVISOR_EXISTS"
    assert same_person.json()["code"] == "OPERATIONAL_CONTEXT.DUPLICATE_ADVISOR_ASSIGNMENT"
    assert non_primary.status_code == 201
    assert other_company.status_code == 201


def test_valid_from_rules(api, company, fake_persons):
    future = _create(api, company["id"], fake_persons.add(), valid_from=_iso(timedelta(days=1)))
    past = _create(api, company["id"], fake_persons.add(), valid_from=_iso(timedelta(days=-30)))

    assert future.status_code == 422
    assert future.json()["code"] == "OPERATIONAL_CONTEXT.INVALID_VALIDITY_PERIOD"
    assert past.status_code == 201


def test_inactive_company_is_422(api, company, fake_persons):
    api.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": company["version"]})

    response = _create(api, company["id"], fake_persons.add())

    assert response.json()["code"] == "OPERATIONAL_CONTEXT.COMPANY_INACTIVE"


def test_close_rules(api, company, fake_persons):
    created = _create(api, company["id"], fake_persons.add(), valid_from=_iso(timedelta(days=-10))).json()
    url = f"/api/v1/advisor-assignments/{created['id']}/close"

    assert api.post(url, json={"version": 1, "valid_to": _iso(timedelta(days=1))}).status_code == 422
    assert api.post(url, json={"version": 1, "valid_to": _iso(timedelta(days=-20))}).status_code == 422

    closed = api.post(url, json={"version": 1, "valid_to": _iso(timedelta(days=-1))})
    assert closed.status_code == 200
    assert closed.json()["status"] == "INACTIVE" and closed.json()["valid_to"] is not None

    again = api.post(url, json={"version": 2})
    assert again.status_code == 409
    assert again.json()["code"] == "OPERATIONAL_CONTEXT.INVALID_STATUS_TRANSITION"


def test_close_with_default_now(api, company, fake_persons):
    created = _create(api, company["id"], fake_persons.add(), valid_from=_iso(timedelta(minutes=-5))).json()
    fake_persons.reset()

    closed = api.post(f"/api/v1/advisor-assignments/{created['id']}/close", json={"version": 1})

    assert closed.status_code == 200 and closed.json()["status"] == "INACTIVE"
    assert fake_persons.count() == 0


def test_history_order_and_filters(api, company, fake_persons):
    old = _create(api, company["id"], fake_persons.add(), valid_from=_iso(timedelta(days=-10))).json()
    api.post(f"/api/v1/advisor-assignments/{old['id']}/close", json={"version": 1, "valid_to": _iso(timedelta(days=-5))})
    new = _create(api, company["id"], fake_persons.add(), valid_from=_iso(timedelta(days=-2))).json()
    helper = _create(api, company["id"], fake_persons.add(), is_primary=False).json()

    history = api.get(_url(company["id"])).json()
    vigentes = api.get(_url(company["id"]), params={"status": "ACTIVE"}).json()
    primarias = api.get(_url(company["id"]), params={"is_primary": "true"}).json()

    assert [item["id"] for item in history["items"]] == [helper["id"], new["id"], old["id"]]
    assert {item["id"] for item in vigentes["items"]} == {new["id"], helper["id"]}
    assert {item["id"] for item in primarias["items"]} == {new["id"], old["id"]}
    assert api.get(f"/api/v1/advisor-assignments/{old['id']}").json()["status"] == "INACTIVE"


def test_no_put_delete_or_reactivation(api, company, fake_persons):
    created = _create(api, company["id"], fake_persons.add()).json()
    url = f"/api/v1/advisor-assignments/{created['id']}"

    assert api.put(url, json={"version": 1}).status_code == 405
    assert api.delete(url).status_code == 405
    assert api.post(f"{url}/reactivate", json={"version": 1}).status_code == 404


def test_later_inactive_person_does_not_change_existing(api, company, fake_persons):
    person = fake_persons.add()
    created = _create(api, company["id"], person).json()
    fake_persons.persons[person] = "INACTIVE"

    assert api.get(f"/api/v1/advisor-assignments/{created['id']}").json()["status"] == "ACTIVE"


def test_member_of_other_company_does_not_see_advisors(api, api_as, company, create_company, make_member, fake_persons):
    created = _create(api, company["id"], fake_persons.add()).json()
    other = create_company()
    make_member(other["id"], "ajeno")
    outsider = api_as("perm:operational-context:all:read", sub="ajeno")

    assert outsider.get(f"/api/v1/advisor-assignments/{created['id']}").status_code == 404
    assert outsider.get(_url(company["id"])).status_code == 404
