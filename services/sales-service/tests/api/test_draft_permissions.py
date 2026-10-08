"""Autorización del borrador (FR-028, FR-029, DS-09, DS-12; RC-05; T036)."""

from __future__ import annotations

from tests.conftest import base, line, sale_body, user_sub


def test_assigned_seller_creates_in_assigned_branch_only(seller, world) -> None:
    assert seller.post(f"{base(world)}/sales", json=sale_body(world)).status_code == 201
    response = seller.post(f"{base(world)}/sales", json={**sale_body(world), "branch_id": str(world.branch_b)})
    assert response.status_code == 403
    assert response.json()["code"] == "SALES.BRANCH_ACCESS_DENIED"


def test_creating_with_lines_requires_detail_permission(make_token, as_token, world, fakes) -> None:
    sub = "sub-solo-ventas"
    fakes.oc.add_member(sub, world.company, branches=(world.branch,))
    token = make_token("perm:sales:sales:create", sub=sub, preferred_username="solo.ventas")
    client = as_token(token)
    assert client.post(f"{base(world)}/sales", json=sale_body(world)).status_code == 201
    response = client.post(f"{base(world)}/sales", json=sale_body(world, line(world.product)))
    assert response.status_code == 403
    assert "perm:" not in response.text


def test_wildcard_does_not_replace_branch_assignment(as_user, world, fakes) -> None:
    fakes.oc.assignments.discard((user_sub("supervisor.test"), world.branch))
    response = as_user("supervisor.test").post(f"{base(world)}/sales", json=sale_body(world))
    assert response.status_code == 403
    assert response.json()["code"] == "SALES.BRANCH_ACCESS_DENIED"


def test_non_member_gets_404(as_user, world, fakes) -> None:
    fakes.oc.members.pop((user_sub("ventas.test"), world.company))
    response = as_user("ventas.test").post(f"{base(world)}/sales", json=sale_body(world))
    assert response.status_code == 404
    assert response.json()["code"] == "SALES.NOT_FOUND"


def test_users_without_sale_write_permission_get_403(as_user, world) -> None:
    for username in ("inventario.test", "compras.test", "reportes.test", "consulta.test"):
        assert as_user(username).post(f"{base(world)}/sales", json=sale_body(world)).status_code == 403


def test_seller_does_not_see_profitability(seller, world) -> None:
    sale = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product))).json()
    assert "has_unknown_cost" not in sale and "cost_known" not in sale["lines"][0]


def test_operational_context_denial(seller, world, fakes) -> None:
    fakes.oc.access_forbidden.add(user_sub("ventas.test"))
    response = seller.post(f"{base(world)}/sales", json=sale_body(world))
    assert response.status_code == 403
    assert response.json()["code"] == "SALES.OPERATIONAL_ACCESS_DENIED"


def test_access_uses_the_user_token(seller, world, fakes) -> None:
    from tests.fakes import subject_of

    seller.post(f"{base(world)}/sales", json=sale_body(world))
    authorization, kind, target = fakes.oc.access_calls[0]
    # Se compara el `sub` del token propagado (el JWT completo cambia con su `iat`): es el del usuario.
    assert subject_of(authorization) == user_sub("ventas.test")
    assert kind == "branch" and target == world.branch
