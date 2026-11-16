"""Paridad de ``v1_companies``, ``v1_branches``, ``v1_application_users`` y ``v1_user_memberships`` (spec 025, T020).

Cada columna de la vista debe coincidir con el mismo campo del GET del propietario, para filas activas e inactivas.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text


def _row(connection, view: str, where: str, params: dict) -> dict:
    row = connection.execute(text(f"SELECT * FROM contract.{view} WHERE {where}"), params).mappings().one()
    return {key: (str(value) if value is not None and not isinstance(value, str) else value) for key, value in row.items()}


def test_companies_and_branches_match_get(api, create_company, create_branch, test_engine):
    company = create_company(timezone="America/Bogota")
    inactive = create_company()
    with_tz = create_branch(company["id"], code="TZ-1", timezone="America/Lima")
    without_tz = create_branch(company["id"], code="TZ-2")
    closed = create_branch(company["id"], code="TZ-3")
    assert api.post(f"/api/v1/branches/{closed['id']}/deactivate", json={"version": closed["version"]}).status_code == 200
    assert api.post(f"/api/v1/companies/{inactive['id']}/deactivate", json={"version": inactive["version"]}).status_code == 200

    with test_engine.connect() as connection:
        for company_id in (company["id"], inactive["id"]):
            body = api.get(f"/api/v1/companies/{company_id}").json()
            view = _row(connection, "v1_companies", "id = :id", {"id": company_id})
            for column in ("id", "status", "organization_identity_id", "default_currency", "timezone"):
                assert view[column] == body[column], column

        for branch in (with_tz, without_tz, closed):
            body = api.get(f"/api/v1/branches/{branch['id']}").json()
            view = _row(connection, "v1_branches", "id = :id", {"id": branch["id"]})
            for column in ("id", "company_id", "code", "name", "status", "company_status", "effective_timezone"):
                assert view[column] == body[column], column

        for status in ("ACTIVE", "INACTIVE"):
            listed = [item["id"] for item in api.get(f"/api/v1/companies/{company['id']}/branches",
                                                      params={"page_size": 100, "status": status}).json()["items"]]
            ordered = connection.execute(
                text("SELECT id FROM contract.v1_branches WHERE company_id = :c AND status = :s ORDER BY created_at, id"),
                {"c": company["id"], "s": status},
            ).scalars().all()
            assert [str(value) for value in ordered] == listed, status


def test_application_users_and_memberships_match_get(api, create_company, make_member, test_engine):
    company = create_company()
    sub = f"user-{uuid4()}"
    active = make_member(company["id"], sub)
    inactive = make_member(company["id"], f"other-{uuid4()}", status="INACTIVE")

    with test_engine.connect() as connection:
        for member_id in (active, inactive):
            body = api.get(f"/api/v1/application-users/{member_id}").json()
            view = _row(connection, "v1_application_users", "id = :id", {"id": member_id})
            for column in ("id", "company_id", "keycloak_user_id", "status", "company_status"):
                assert view[column] == body[column], column

        memberships = connection.execute(
            text("SELECT application_user_id, company_id, status, company_status FROM contract.v1_user_memberships "
                 "WHERE keycloak_user_id = :sub"),
            {"sub": sub},
        ).mappings().all()
        assert [(str(row["application_user_id"]), str(row["company_id"]), row["status"], row["company_status"])
                for row in memberships] == [(active, company["id"], "ACTIVE", "ACTIVE")]
