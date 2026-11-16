"""Paridad de ``contract.v1_operational_access`` con ``GET /operational-access`` (spec 025, T019).

Para cada usuario y cada empresa o sucursal pedida, la fila de la vista interpretada como lo hará el consumidor
(sin fila → ``USER_NOT_MEMBER``; ``denial_reason`` → esa causa; si no, permitido) debe dar el mismo ``allowed``,
``reason``, ``company_id`` y ``application_user_id`` que la vía propia de ``OperationalAccessService.check``.

Ningún consumidor envía ``permission``; la evaluación del permiso con el token la cubre la prueba del adaptador.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

URL = "/api/v1/operational-access"
READ = "perm:operational-context:application_users:read"
UNKNOWN = "00000000-0000-4000-8000-000000000999"

BY_COMPANY = """
SELECT company_id, application_user_id, denial_reason FROM contract.v1_operational_access
 WHERE keycloak_user_id = :sub AND company_id = :company_id AND branch_id IS NULL
"""
BY_BRANCH = """
SELECT company_id, application_user_id, denial_reason FROM contract.v1_operational_access
 WHERE keycloak_user_id = :sub AND branch_id = :branch_id
"""


def from_view(connection, sub: str, *, company_id: str | None = None, branch_id: str | None = None) -> dict:
    """Lo mismo que hará el adaptador del consumidor con la fila de la vista."""
    if branch_id is not None:
        rows = connection.execute(text(BY_BRANCH), {"sub": sub, "branch_id": branch_id}).mappings().all()
    else:
        rows = connection.execute(text(BY_COMPANY), {"sub": sub, "company_id": company_id}).mappings().all()
    assert len(rows) <= 1, "la vista debe dar a lo sumo una fila por usuario y destino"
    if not rows:
        return {"allowed": False, "reason": "USER_NOT_MEMBER", "company_id": company_id, "application_user_id": None}
    row = rows[0]
    return {
        "allowed": row["denial_reason"] is None,
        "reason": row["denial_reason"],
        "company_id": str(row["company_id"]),
        "application_user_id": str(row["application_user_id"]),
    }


def from_api(client, *, company_id: str | None = None, branch_id: str | None = None) -> dict:
    params = {"branch_id": branch_id} if branch_id is not None else {"company_id": company_id}
    response = client.get(URL, params=params)
    assert response.status_code == 200, response.text
    body = response.json()
    return {key: body[key] for key in ("allowed", "reason", "company_id", "application_user_id")}


@pytest.fixture
def world(api, create_company, create_branch, make_member, test_engine):
    c = create_company()
    d = create_company()
    f = create_company()
    s1, s2, s3, s4 = (create_branch(c["id"], code=f"S-{n}") for n in range(1, 5))
    d1 = create_branch(d["id"], code="D-1")
    fb = create_branch(f["id"], code="F-1")

    subs = {name: f"{name}-{uuid4()}" for name in ("ok", "inactiva_reciente", "activa_y_nueva_inactiva", "inactiva_asignada")}

    def assign(member_id: str, branch_id: str) -> dict:
        response = api.post(f"/api/v1/application-users/{member_id}/user-branches", json={"branch_id": branch_id})
        assert response.status_code == 201, response.text
        return response.json()

    ok = make_member(c["id"], subs["ok"])
    for branch in (s1, s3, s4):
        assign(ok, branch["id"])
    ok_d = make_member(d["id"], subs["ok"])
    assign(ok_d, d1["id"])

    # Dos membresías inactivas: gana la de updated_at más reciente.
    old = make_member(c["id"], subs["inactiva_reciente"])
    assign(old, s1["id"])
    newer = make_member(c["id"], subs["inactiva_reciente"], status="INACTIVE")
    # Una activa (más antigua) y una inactiva más nueva: gana la activa.
    active = make_member(c["id"], subs["activa_y_nueva_inactiva"])
    assign(active, s1["id"])
    make_member(c["id"], subs["activa_y_nueva_inactiva"], status="INACTIVE")
    # Membresía inactiva con asignación activa.
    inactive_assigned = make_member(c["id"], subs["inactiva_asignada"])
    assign(inactive_assigned, s1["id"])

    with test_engine.begin() as connection:
        connection.execute(
            text("UPDATE application_users SET status='INACTIVE', updated_at = now() - interval '2 days' WHERE id = :id"),
            {"id": old},
        )
        connection.execute(
            text("UPDATE application_users SET updated_at = now() - interval '1 day' WHERE id = :id"), {"id": newer}
        )
        connection.execute(
            text("UPDATE application_users SET updated_at = now() - interval '3 days' WHERE id = :id"), {"id": active}
        )
        connection.execute(
            text("UPDATE application_users SET status='INACTIVE', updated_at = now() WHERE id = :id"),
            {"id": inactive_assigned},
        )

    assignment = next(
        item
        for item in api.get(f"/api/v1/application-users/{ok}/user-branches").json()["items"]
        if item["branch_id"] == s3["id"]
    )
    assert api.post(f"/api/v1/user-branches/{assignment['id']}/deactivate", json={"version": assignment["version"]}).status_code == 200
    assert api.post(f"/api/v1/branches/{s4['id']}/deactivate", json={"version": s4["version"]}).status_code == 200
    assert api.post(f"/api/v1/companies/{d['id']}/deactivate", json={"version": d["version"]}).status_code == 200

    return {
        "subs": subs,
        "companies": {"C": c["id"], "D": d["id"], "F": f["id"], "UNKNOWN": UNKNOWN},
        "branches": {"S1": s1["id"], "S2": s2["id"], "S3": s3["id"], "S4": s4["id"], "D1": d1["id"],
                     "FB": fb["id"], "UNKNOWN": UNKNOWN},
        "expected_member": {"inactiva_reciente": newer, "activa_y_nueva_inactiva": active},
    }


def test_matrix_matches_operational_access(world, api_as, test_engine):
    observed_reasons = set()
    with test_engine.connect() as connection:
        for name, sub in world["subs"].items():
            client = api_as(READ, sub=sub)
            for label, company_id in world["companies"].items():
                expected = from_api(client, company_id=company_id)
                assert from_view(connection, sub, company_id=company_id) == expected, (name, "empresa", label)
                observed_reasons.add(expected["reason"])
            for label, branch_id in world["branches"].items():
                expected = from_api(client, branch_id=branch_id)
                assert from_view(connection, sub, branch_id=branch_id) == expected, (name, "sucursal", label)
                observed_reasons.add(expected["reason"])

    assert observed_reasons >= {
        None,
        "USER_NOT_MEMBER",
        "USER_MEMBERSHIP_INACTIVE",
        "COMPANY_INACTIVE",
        "BRANCH_INACTIVE",
        "BRANCH_NOT_ASSIGNED",
        "USER_BRANCH_INACTIVE",
    }


def test_membership_choice(world, test_engine):
    with test_engine.connect() as connection:
        for name, member_id in world["expected_member"].items():
            row = from_view(connection, world["subs"][name], company_id=world["companies"]["C"])
            assert row["application_user_id"] == member_id, name


def test_view_is_read_only_projection(test_engine):
    with test_engine.connect() as connection:
        columns = connection.execute(
            text(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='contract' "
                "AND table_name='v1_operational_access' ORDER BY ordinal_position"
            )
        ).scalars().all()
    assert columns == ["keycloak_user_id", "company_id", "branch_id", "application_user_id", "denial_reason"]
