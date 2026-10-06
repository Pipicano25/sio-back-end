"""Solo cuentas de servicio y cada una su tipo (RC-01; T026)."""

from __future__ import annotations

import pytest

from tests.conftest import ENTRIES_CREATE, OUTPUTS_CREATE, line, operation_body, user_sub

ENTRIES = "/api/v1/inventory-entries"


@pytest.mark.parametrize("roles", [("perm:all:all:all",), ("perm:all:all:create",), (ENTRIES_CREATE,)])
def test_humans_cannot_apply_even_with_wildcards(as_token, make_token, world, roles) -> None:
    token = make_token(*roles, sub=user_sub("admin.test"), preferred_username="admin.test")
    response = as_token(token).post(ENTRIES, json=operation_body(world, line(world.products[0], "1")))
    assert response.status_code == 403


def test_same_body_for_human_and_missing_permission(as_token, make_token, sales, world) -> None:
    human = as_token(make_token("perm:all:all:all", sub="sub-x", preferred_username="admin.test"))
    body = operation_body(world, line(world.products[0], "1"))
    by_human = human.post(ENTRIES, json=body).json()
    by_service = sales.post(ENTRIES, json=body).json()
    for item in (by_human, by_service):
        item.pop("trace_id")
    assert by_human == by_service
    assert "perm:" not in str(by_human)


def test_service_account_without_entries_permission(service_token, as_token, world) -> None:
    client = as_token(service_token(OUTPUTS_CREATE, client_id="sales-service"))
    assert client.post(ENTRIES, json=operation_body(world, line(world.products[0], "1"))).status_code == 403


def test_purchase_client_applies_entries(purchase, world) -> None:
    assert purchase.post(ENTRIES, json=operation_body(world, line(world.products[0], "1"))).status_code == 201
