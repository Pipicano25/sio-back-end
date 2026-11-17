"""Paridad de ``contract.v1_user_memberships`` con ``GET /me/operational-context`` (spec 025, T057).

Para cada usuario, las filas de la vista ordenadas por ``created_at, id`` (lo que hará Commercial Relationship en el
resumen de empresas) deben coincidir con las membresías de ``/me/operational-context``: mismas membresías, en el mismo
orden, con el mismo ``application_user_id``, ``company_id``, ``status`` y ``company_status``. Se cubren membresías
activas e inactivas, empresas activas e inactivas, la misma empresa repetida (una ``ACTIVE`` como máximo por
empresa y usuario, ``uq_application_users_company_id_keycloak_user_id_active``) y un ``created_at`` que no sigue el orden
de inserción.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text

URL = "/api/v1/me/operational-context"
READ = "perm:operational-context:application_users:read"

FROM_VIEW = """
SELECT application_user_id, company_id, status, company_status FROM contract.v1_user_memberships
 WHERE keycloak_user_id = :sub ORDER BY created_at, application_user_id
"""


def _from_view(connection, sub: str) -> list[tuple[str, str, str, str]]:
    rows = connection.execute(text(FROM_VIEW), {"sub": sub}).mappings().all()
    return [(str(r["application_user_id"]), str(r["company_id"]), r["status"], r["company_status"]) for r in rows]


def _from_api(client) -> list[tuple[str, str, str, str]]:
    response = client.get(URL)
    assert response.status_code == 200, response.text
    return [
        (m["application_user_id"], m["company_id"], m["status"], m["company_status"])
        for m in response.json()["memberships"]
    ]


def test_memberships_match_me_operational_context(api, api_as, create_company, make_member, test_engine):
    active_company = create_company()
    closed_company = create_company()
    repeated_company = create_company()
    assert api.post(
        f"/api/v1/companies/{closed_company['id']}/deactivate", json={"version": closed_company["version"]}
    ).status_code == 200

    sub = f"miembro-{uuid4()}"
    other = f"otro-{uuid4()}"
    created = [
        make_member(active_company["id"], sub),
        make_member(closed_company["id"], sub),
        make_member(repeated_company["id"], sub),
        make_member(repeated_company["id"], sub, status="INACTIVE"),
        make_member(repeated_company["id"], sub, status="INACTIVE"),
        make_member(active_company["id"], sub, status="INACTIVE"),
    ]
    make_member(active_company["id"], other)

    # El orden de `created_at` no sigue el de inserción.
    with test_engine.begin() as connection:
        for days, member_id in zip((1, 6, 3, 2, 5, 4), created, strict=True):
            connection.execute(
                text("UPDATE application_users SET created_at = now() - make_interval(days => :d) WHERE id = :id"),
                {"d": days, "id": member_id},
            )

    expected = _from_api(api_as(READ, sub=sub))
    with test_engine.connect() as connection:
        observed = _from_view(connection, sub)

    assert observed == expected
    assert len(observed) == 6
    assert [row[0] for row in observed] == [created[i] for i in (1, 4, 5, 2, 3, 0)]
    assert {(row[2], row[3]) for row in observed} == {
        ("ACTIVE", "ACTIVE"),
        ("INACTIVE", "ACTIVE"),
        ("ACTIVE", "INACTIVE"),
    }


def test_user_without_memberships(api_as, test_engine):
    sub = f"sin-membresias-{uuid4()}"
    assert _from_api(api_as(READ, sub=sub)) == []
    with test_engine.connect() as connection:
        assert _from_view(connection, sub) == []
