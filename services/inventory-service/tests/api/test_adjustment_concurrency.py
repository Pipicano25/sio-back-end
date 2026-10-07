"""Ajustes negativos y salidas simultáneos sobre las mismas capas (RC-14, RN-03; T036)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from tests.api.test_fifo_concurrency import assert_layers_are_consistent
from tests.conftest import OPERATOR_ROLES, line, operation_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def test_negative_adjustments_and_outputs_never_overdraw(app, operator, service_token, user_token, world, test_engine) -> None:
    product = world.products[0]
    for cost in ("10", "20", "30"):
        assert operator.post(ENTRIES, json=operation_body(world, line(product, "10", unit_cost=cost))).status_code == 201

    adjustments = f"/api/v1/companies/{world.company}/inventory-adjustments"
    requests = []
    for i in range(40):
        if i % 2:
            requests.append((OUTPUTS, operation_body(world, line(product, "1"), origin_type="SALE"), service_token(*OPERATOR_ROLES)))
        else:
            body = {
                "adjustment_key": str(uuid4()),
                "branch_id": str(world.branch),
                "company_product_id": str(product),
                "adjustment_type": "NEGATIVE",
                "quantity": "1",
                "reason": "Merma ficticia",
            }
            requests.append((adjustments, body, user_token("inventario.test")))

    def send(request):
        url, body, token = request
        client = TestClient(app, raise_server_exceptions=False)
        return client.post(url, json=body, headers={"Authorization": f"Bearer {token}"}).status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        statuses = list(pool.map(send, requests))

    assert 500 not in statuses and 503 not in statuses
    assert statuses.count(201) == 30
    assert statuses.count(409) == 10
    with test_engine.connect() as connection:
        quantity = connection.execute(text("SELECT quantity FROM inventory_balances")).scalar_one()
    assert quantity == D(0)
    assert_layers_are_consistent(test_engine)
