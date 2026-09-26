"""Unicidad de membresía `ACTIVE` bajo concurrencia (RC-04, R-04)."""

from sqlalchemy import text

from tests.api.test_uniqueness_concurrency import _parallel


def _active_members(test_engine, company_id) -> int:
    with test_engine.connect() as connection:
        return connection.execute(
            text("SELECT count(*) FROM application_users WHERE company_id = :c AND status = 'ACTIVE'"),
            {"c": company_id},
        ).scalar_one()


def test_same_person_in_parallel(api, create_company, fake_accounts, fake_persons, test_engine):
    company = create_company()
    person = str(fake_persons.add())
    subs = iter([fake_accounts.add("uno"), fake_accounts.add("dos")])

    def create():
        return api.post(
            f"/api/v1/companies/{company['id']}/application-users",
            json={"keycloak_user_id": next(subs), "person_identity_id": person, "display_name": "P"},
        )

    assert _parallel(create) == [201, 409]
    assert _active_members(test_engine, company["id"]) == 1


def test_same_account_in_parallel(api, create_company, fake_accounts, fake_persons, test_engine):
    company = create_company()
    sub = fake_accounts.add("tres")
    persons = iter([str(fake_persons.add()), str(fake_persons.add())])

    def create():
        return api.post(
            f"/api/v1/companies/{company['id']}/application-users",
            json={"keycloak_user_id": sub, "person_identity_id": next(persons), "display_name": "P"},
        )

    assert _parallel(create) == [201, 409]
    assert _active_members(test_engine, company["id"]) == 1
