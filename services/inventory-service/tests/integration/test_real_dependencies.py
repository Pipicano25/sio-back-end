"""Integración real con Keycloak, Operational Context y Commercial Relationship (T061).

Ejecutar con `pytest -m integration` con el entorno integrado en marcha (inventory-service en
`INVENTORY_INTEGRATION_BASE_URL`, Keycloak reconstruido desde la plantilla con los clientes
`inventory-service` e `inventory-test-operator`). Las dos últimas pruebas detienen y vuelven a
iniciar `sio-operational-context-service` y `sio-commercial-relationship-service`.
"""

from __future__ import annotations

import subprocess
import time

import httpx
import pytest

from tests.integration.support import (
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    OPERATIONAL_CONTEXT,
    operation,
    reversal,
    user_client,
)

pytestmark = pytest.mark.integration


def _balance(client, world, product) -> str:
    response = client.get(f"{INVENTORY}/companies/{world.company}/branches/{world.branch}/balances/{product}")
    assert response.status_code == 200, response.text
    return response.json()["quantity"]


def test_entry_output_shortage_and_reversals_with_real_references(operator, real_world) -> None:
    world = real_world
    a, b = world.products
    # Los datos reales se comparten en la sesión: se compara contra el saldo inicial.
    start_a = float(_balance(operator, world, a))
    start_b = float(_balance(operator, world, b))
    entry = operator.post(f"{INVENTORY}/inventory-entries", json=operation(world, (a, "10"), (b, "4"), unit_cost="1500.25"))
    assert entry.status_code == 201, entry.text
    assert entry.json()["movements"][0]["unit_cost"] == "1500.2500"

    output = operator.post(f"{INVENTORY}/inventory-outputs", json=operation(world, (a, "3"), origin_type="SALE"))
    assert output.status_code == 201, output.text
    assert float(_balance(operator, world, a)) == start_a + 7

    too_much = f"{start_b + 4 + 1:.4f}"
    shortage = operator.post(f"{INVENTORY}/inventory-outputs", json=operation(world, (a, "1"), (b, too_much), origin_type="SALE"))
    assert shortage.status_code == 409
    assert shortage.json()["code"] == "INVENTORY.INSUFFICIENT_STOCK"
    assert float(_balance(operator, world, a)) == start_a + 7

    foreign = operator.post(
        f"{INVENTORY}/inventory-outputs/{output.json()['id']}/reversal", json=reversal(world, world.foreign_company)
    )
    assert foreign.status_code == 404

    reversed_output = operator.post(f"{INVENTORY}/inventory-outputs/{output.json()['id']}/reversal", json=reversal(world))
    assert reversed_output.status_code == 201, reversed_output.text
    assert float(_balance(operator, world, a)) == start_a + 10


def test_product_without_inventory_control_is_rejected(operator, real_world) -> None:
    response = operator.post(f"{INVENTORY}/inventory-entries", json=operation(real_world, (real_world.no_control_product, "1")))
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "INVENTORY_CONTROL_DISABLED"


@pytest.mark.parametrize("username", ["admin.test", "supervisor.test"])
def test_real_humans_cannot_apply(real_world, username) -> None:
    with user_client(username) as client:
        response = client.post(f"{INVENTORY}/inventory-entries", json=operation(real_world, (real_world.products[0], "1")))
    assert response.status_code == 403
    assert "perm:" not in response.text


def test_real_users_reading_with_membership_and_permissions(operator, real_world) -> None:
    operator.post(f"{INVENTORY}/inventory-entries", json=operation(real_world, (real_world.products[1], "2")))
    base = f"{INVENTORY}/companies/{real_world.company}/branches/{real_world.branch}"
    with user_client("inventario.test") as inventario:
        assert inventario.get(f"{base}/balances").status_code == 200
        assert inventario.get(f"{base}/kardex/{real_world.products[1]}").json()["items"]
    with user_client("compras.test") as compras:
        assert compras.get(f"{base}/balances").status_code == 403
    with user_client("admin.test") as admin:
        foreign = f"{INVENTORY}/companies/{real_world.foreign_company}/branches/{real_world.branch}/balances"
        assert admin.get(foreign).status_code == 404


def _stop_and_check(container: str, health_url: str, call, dependency: str) -> None:
    subprocess.run(["docker", "stop", container], check=True, capture_output=True)
    try:
        response = call()
        assert response.status_code == 503, response.text
        assert response.json()["dependency"] == dependency
    finally:
        subprocess.run(["docker", "start", container], check=True, capture_output=True)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                if httpx.get(health_url, timeout=5).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(2)


def test_operational_context_down_returns_503(operator, real_world) -> None:
    body = operation(real_world, (real_world.products[0], "1"))
    _stop_and_check(
        "sio-operational-context-service",
        f"{OPERATIONAL_CONTEXT.removesuffix('/api/v1')}/health/ready",
        lambda: operator.post(f"{INVENTORY}/inventory-entries", json=body),
        "operational-context",
    )
    assert operator.post(f"{INVENTORY}/inventory-entries", json=body).status_code == 201


def test_commercial_relationship_down_returns_503(operator, real_world) -> None:
    body = operation(real_world, (real_world.products[0], "1"))
    _stop_and_check(
        "sio-commercial-relationship-service",
        f"{COMMERCIAL_RELATIONSHIP.removesuffix('/api/v1')}/health/ready",
        lambda: operator.post(f"{INVENTORY}/inventory-entries", json=body),
        "commercial-relationship",
    )
    assert operator.post(f"{INVENTORY}/inventory-entries", json=body).status_code == 201
