"""Autorización de conteos: rutas 14–18 con las reglas de los ajustes (RC-11; DS-14; T041)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.conftest import COUNTS_CREATE, user_sub


def base(company) -> str:
    return f"/api/v1/companies/{company}/inventory-counts"


@pytest.fixture
def count(as_user, world):
    response = as_user("inventario.test").post(base(world.company), json={"branch_id": str(world.branch)})
    assert response.status_code == 201, response.text
    return response.json()


def calls(world, count):
    root = f"{base(world.company)}/{count['id']}"
    return [
        ("POST", base(world.company), {"branch_id": str(world.branch)}),
        ("POST", f"{root}/start", {"version": 1}),
        ("PUT", f"{root}/details/{world.products[0]}", {"counted_quantity": "1"}),
        ("POST", f"{root}/complete", {"completion_key": str(uuid4()), "version": 1}),
        ("POST", f"{root}/cancel", {"reason": "Motivo", "version": 1}),
    ]


def test_service_accounts_are_forbidden(as_token, service_token, world, count) -> None:
    client = as_token(service_token("perm:all:all:all", COUNTS_CREATE))
    for method, url, body in calls(world, count):
        response = client.request(method, url, json=body)
        assert (response.status_code, response.json()["code"]) == (403, "INVENTORY.FORBIDDEN"), url


def test_users_without_permission_are_forbidden(as_user, world, count) -> None:
    for username in ("compras.test", "ventas.test", "reportes.test", "consulta.test"):
        for method, url, body in calls(world, count):
            assert as_user(username).request(method, url, json=body).status_code == 403, (username, url)


def test_user_not_assigned_to_the_branch(as_user, world, fake_oc, count) -> None:
    fake_oc.assign(user_sub("inventario.test"), world.branch, status="INACTIVE")
    for method, url, body in calls(world, count):
        response = as_user("inventario.test").request(method, url, json=body)
        assert (response.status_code, response.json()["code"]) == (403, "INVENTORY.BRANCH_ACCESS_DENIED"), url


def test_non_member_gets_not_found(as_user, world, fake_oc, count) -> None:
    fake_oc.add_member(user_sub("inventario.test"), world.company, status="INACTIVE")
    for method, url, body in calls(world, count):
        assert as_user("inventario.test").request(method, url, json=body).status_code == 404, url


def test_count_of_another_company_is_not_found(as_user, world, count) -> None:
    other = f"{base(world.other_company)}/{count['id']}/start"
    assert as_user("inventario.test").post(other, json={"version": 1}).status_code == 404
    assert as_user("inventario.test").post(f"{base(world.company)}/{uuid4()}/start", json={"version": 1}).status_code == 404
