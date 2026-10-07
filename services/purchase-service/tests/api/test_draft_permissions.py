"""Autorización del borrador (FR-041, DS-09, DS-10; RC-04, RC-05; T033)."""

from __future__ import annotations

from tests.conftest import base, line, purchase_body, user_sub


def test_assigned_buyer_creates_in_assigned_branch_only(buyer, world) -> None:
    assert buyer.post(f"{base(world)}/purchases", json=purchase_body(world)).status_code == 201
    response = buyer.post(f"{base(world)}/purchases", json={**purchase_body(world), "branch_id": str(world.branch_b)})
    assert response.status_code == 403
    assert response.json()["code"] == "PURCHASE.BRANCH_ACCESS_DENIED"


def test_creating_with_lines_requires_detail_permission(make_token, as_token, world, fakes) -> None:
    sub = "sub-solo-compras"
    fakes.oc.add_member(sub, world.company, branches=(world.branch,))
    token = make_token("perm:purchase:purchases:create", sub=sub, preferred_username="solo.compras")
    client = as_token(token)
    assert client.post(f"{base(world)}/purchases", json=purchase_body(world)).status_code == 201
    response = client.post(f"{base(world)}/purchases", json=purchase_body(world, line(world.product)))
    assert response.status_code == 403
    assert "perm:" not in response.text


def test_wildcard_does_not_replace_branch_assignment(as_user, world, fakes) -> None:
    fakes.oc.assignments.discard((user_sub("supervisor.test"), world.branch))
    response = as_user("supervisor.test").post(f"{base(world)}/purchases", json=purchase_body(world))
    assert response.status_code == 403
    assert response.json()["code"] == "PURCHASE.BRANCH_ACCESS_DENIED"


def test_non_member_gets_404(as_user, world, fakes) -> None:
    fakes.oc.members.pop((user_sub("compras.test"), world.company))
    response = as_user("compras.test").post(f"{base(world)}/purchases", json=purchase_body(world))
    assert response.status_code == 404
    assert response.json()["code"] == "PURCHASE.NOT_FOUND"


def test_users_without_purchase_permission_get_403(as_user, world) -> None:
    for username in ("inventario.test", "ventas.test", "reportes.test", "consulta.test"):
        assert as_user(username).post(f"{base(world)}/purchases", json=purchase_body(world)).status_code == 403


def test_operational_context_denial(buyer, world, fakes) -> None:
    fakes.oc.access_forbidden.add(user_sub("compras.test"))
    response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world))
    assert response.status_code == 403
    assert response.json()["code"] == "PURCHASE.OPERATIONAL_ACCESS_DENIED"


def test_access_uses_the_user_token(buyer, world, fakes) -> None:
    from tests.fakes import subject_of

    buyer.post(f"{base(world)}/purchases", json=purchase_body(world))
    authorization, kind, target = fakes.oc.access_calls[0]
    # Se compara el `sub` del token propagado (el JWT completo cambia con su `iat`): es el del usuario.
    assert subject_of(authorization) == user_sub("compras.test")
    assert kind == "branch" and target == world.branch
