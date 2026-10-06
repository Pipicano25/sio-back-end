"""Cada consumidor revierte solo su tipo; los humanos nunca (RC-01; T042)."""

from __future__ import annotations

from tests.conftest import line, operation_body, reversal_body, user_sub

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def test_each_consumer_reverses_only_its_type(operator, purchase, sales, world) -> None:
    product = world.products[0]
    entry = purchase.post(ENTRIES, json=operation_body(world, line(product, "5"))).json()
    output = sales.post(OUTPUTS, json=operation_body(world, line(product, "1"), origin_type="SALE")).json()

    assert sales.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world)).status_code == 403
    assert purchase.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world)).status_code == 403
    assert sales.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world)).status_code == 201
    assert purchase.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world)).status_code == 201


def test_humans_cannot_reverse(operator, as_token, make_token, world) -> None:
    entry = operator.post(ENTRIES, json=operation_body(world, line(world.products[0], "5"))).json()
    human = as_token(make_token("perm:all:all:all", sub=user_sub("admin.test"), preferred_username="admin.test"))
    assert human.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world)).status_code == 403
