"""Integración real de la Fase B: ajustes, conteos, políticas y valoración (T059).

Ejecutar con `pytest -m integration` con el entorno integrado en marcha y Keycloak reconstruido desde
la plantilla con los permisos de la 013. Los datos son ficticios (`support.build_world`):
`inventario.test` y `admin.test` están asignados a la sucursal principal y a ninguna otra.
"""

from __future__ import annotations

import subprocess
import time
from uuid import uuid4

import httpx
import pytest

from tests.integration.support import INVENTORY, OPERATIONAL_CONTEXT, operation, reversal, user_client

pytestmark = pytest.mark.integration


def adjustment(world, product, kind="NEGATIVE", quantity="1", *, branch=None, unit_cost=None) -> dict:
    return {
        "adjustment_key": str(uuid4()),
        "branch_id": branch or world.branch,
        "company_product_id": product,
        "adjustment_type": kind,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "reason": "Ajuste ficticio de validación INV",
    }


@pytest.fixture(scope="module")
def stocked(operator, real_world):
    product = real_world.products[0]
    entry = operator.post(f"{INVENTORY}/inventory-entries", json=operation(real_world, (product, "20"), unit_cost="250"))
    assert entry.status_code == 201, entry.text
    return product


def test_entries_require_cost_and_layers_take_the_real_company_currency(admin, operator, real_world, stocked) -> None:
    body = operation(real_world, (real_world.products[0], "1"))
    body["lines"][0].pop("unit_cost")
    response = operator.post(f"{INVENTORY}/inventory-entries", json=body)
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "UNIT_COST_REQUIRED"

    currency = admin.get(f"{OPERATIONAL_CONTEXT}/companies/{real_world.company}").json()["default_currency"]
    layers = operator.get(
        f"{INVENTORY}/companies/{real_world.company}/branches/{real_world.branch}/valuation/{stocked}/layers"
    ).json()["items"]
    assert layers and all(layer["currency_code"] == currency for layer in layers)


def test_fifo_end_to_end(operator, real_world) -> None:
    product = real_world.products[1]
    start = operator.get(
        f"{INVENTORY}/companies/{real_world.company}/branches/{real_world.branch}/balances/{product}"
    ).json()
    assert start["has_unknown_cost"] is False
    for quantity, cost in (("10", "1000"), ("5", "1300")):
        assert operator.post(
            f"{INVENTORY}/inventory-entries", json=operation(real_world, (product, quantity), unit_cost=cost)
        ).status_code == 201
    # Consume primero lo que hubiera antes (más antiguo) y luego las capas nuevas: se valida contra los consumos.
    sale = operator.post(f"{INVENTORY}/inventory-outputs", json=operation(real_world, (product, "2"), origin_type="SALE"))
    assert sale.status_code == 201, sale.text
    movement = sale.json()["movements"][0]
    consumptions = operator.get(
        f"{INVENTORY}/companies/{real_world.company}/inventory-movements/{movement['id']}/cost-consumptions"
    ).json()["items"]
    assert sum(float(item["cost_amount"]) for item in consumptions) == float(movement["movement_value"])
    restored = operator.post(f"{INVENTORY}/inventory-outputs/{sale.json()['id']}/reversal", json=reversal(real_world))
    assert restored.status_code == 201
    assert restored.json()["movements"][0]["movement_value"] == movement["movement_value"]


def test_assigned_user_adjusts_and_unassigned_branch_is_denied(real_world, stocked) -> None:
    with user_client("inventario.test") as inventario:
        applied = inventario.post(f"{INVENTORY}/companies/{real_world.company}/inventory-adjustments", json=adjustment(real_world, stocked))
        assert applied.status_code == 201, applied.text
        assert applied.json()["application_user_id"] == real_world.inventario_user
        # El producto puede tener capas más antiguas de otras pruebas de la sesión: el costo es el de sus consumos FIFO.
        movement = applied.json()["movement"]
        consumptions = inventario.get(
            f"{INVENTORY}/companies/{real_world.company}/inventory-movements/{movement['id']}/cost-consumptions"
        ).json()["items"]
        assert sum(float(item["cost_amount"]) for item in consumptions) == float(applied.json()["adjustment_value"])

        denied = inventario.post(
            f"{INVENTORY}/companies/{real_world.company}/inventory-adjustments",
            json=adjustment(real_world, stocked, "POSITIVE", unit_cost="1", branch=real_world.branch_b),
        )
        assert denied.status_code == 403
        assert denied.json()["code"] == "INVENTORY.BRANCH_ACCESS_DENIED"


def test_service_account_and_users_without_permission_cannot_adjust(operator, real_world, stocked) -> None:
    url = f"{INVENTORY}/companies/{real_world.company}/inventory-adjustments"
    assert operator.post(url, json=adjustment(real_world, stocked)).status_code == 403
    with user_client("compras.test") as compras:
        assert compras.post(url, json=adjustment(real_world, stocked)).status_code == 403


def test_count_end_to_end(real_world, stocked) -> None:
    base = f"{INVENTORY}/companies/{real_world.company}/inventory-counts"
    with user_client("inventario.test") as inventario:
        count = inventario.post(base, json={"branch_id": real_world.branch, "observations": "Conteo ficticio INV"})
        assert count.status_code == 201, count.text
        count_id = count.json()["id"]
        started = inventario.post(f"{base}/{count_id}/start", json={"version": 1})
        assert started.status_code == 200, started.text
        detail = inventario.put(f"{base}/{count_id}/details/{stocked}", json={"counted_quantity": "5"})
        assert detail.status_code == 200, detail.text
        difference = float(detail.json()["difference_quantity"])
        completed = inventario.post(
            f"{base}/{count_id}/complete", json={"completion_key": str(uuid4()), "version": started.json()["version"]}
        )
        assert completed.status_code == 200, completed.text
        data = completed.json()
        assert data["status"] == "COMPLETED"
        assert len(data["adjustments"]) == (1 if difference else 0)

        denied = inventario.post(base, json={"branch_id": real_world.branch_b})
        assert denied.status_code == 403
        assert denied.json()["code"] == "INVENTORY.BRANCH_ACCESS_DENIED"


def test_policies_by_administrators_only(real_world) -> None:
    url = f"{INVENTORY}/companies/{real_world.company}/inventory-policy"
    body = {"inventory_system": "PERPETUAL", "valuation_method": "FIFO", "replenishment_strategy": "STANDARD"}
    with user_client("inventario.test") as inventario:
        assert inventario.get(url).json()["registered"] is False
        assert inventario.post(url, json=body).status_code == 403
    with user_client("compras.test") as compras:
        assert compras.post(url, json=body).status_code == 403
    with user_client("admin.test") as admin_user:
        created = admin_user.post(url, json=body)
        assert created.status_code == 201, created.text
        assert admin_user.post(url, json=body).status_code == 409


def test_operational_context_down_returns_503_for_adjustments(real_world, stocked) -> None:
    url = f"{INVENTORY}/companies/{real_world.company}/inventory-adjustments"
    with user_client("inventario.test") as inventario:
        subprocess.run(["docker", "stop", "sio-operational-context-service"], check=True, capture_output=True)
        try:
            response = inventario.post(url, json=adjustment(real_world, stocked))
            assert response.status_code == 503, response.text
            assert response.json()["dependency"] == "operational-context"
        finally:
            subprocess.run(["docker", "start", "sio-operational-context-service"], check=True, capture_output=True)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                try:
                    if httpx.get(f"{OPERATIONAL_CONTEXT.removesuffix('/api/v1')}/health/ready", timeout=5).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(2)
        assert inventario.post(url, json=adjustment(real_world, stocked)).status_code == 201
