"""Evolución de existencias de una sucursal (spec 023, INV-R1).

Requieren la base de pruebas de Inventory (`INVENTORY_TEST_DATABASE_URL`). Por la estrategia aprobada de la spec 023
no se crean bases temporales: se ejecutan cuando exista una base de pruebas aislada autorizada.

Cubren: saldo inicial por el último movimiento anterior, sumas por tipo (entradas, salidas, reversos y ajustes),
saldo final e identidad, productos sin movimientos con saldo, ausencia total de costos, permiso propio
`stock_evolution:read` (que **no** abre el kardex), `reportes` sin `movements:read`, aislamiento entre empresas y
sucursales y validación del período.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from tests.conftest import STOCK_EVOLUTION_READ, line, operation_body, reversal_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"
COST_KEYS = {"unit_cost", "movement_value", "cost_known", "inventory_value", "average_unit_cost", "layers"}
FIELDS = ("opening_quantity", "entries", "outputs", "entry_reversals", "output_reversals", "positive_adjustments",
          "negative_adjustments", "closing_quantity")


def url(world, branch=None, company=None) -> str:
    return f"/api/v1/companies/{company or world.company}/branches/{branch or world.branch}/stock-evolution"


def window(start: datetime, end: datetime) -> dict:
    return {"from": start.isoformat(), "to": end.isoformat()}


def adjustment(world, product, kind, quantity):
    return {"adjustment_key": str(uuid4()), "branch_id": str(world.branch), "company_product_id": str(product),
            "adjustment_type": kind, "quantity": quantity, "unit_cost": None, "reason": "Ajuste de prueba"}


@pytest.fixture
def history(operator, as_user, world):
    """Producto 0: entrada 10, salida 4 y su reverso, entrada 3 y su reverso, ajuste +2 y −1 (saldo final 11).
    Producto 1: entrada 5 (saldo sin movimientos después)."""
    product, other = world.products[0], world.products[1]
    assert operator.post(ENTRIES, json=operation_body(world, line(other, "5", unit_cost="900"))).status_code == 201
    middle = datetime.now(UTC)
    assert operator.post(ENTRIES, json=operation_body(world, line(product, "10", unit_cost="1000"))).status_code == 201
    output = operator.post(OUTPUTS, json=operation_body(world, line(product, "4"), origin_type="SALE"))
    assert output.status_code == 201
    assert operator.post(f"{OUTPUTS}/{output.json()['id']}/reversal", json=reversal_body(world)).status_code == 201
    entry = operator.post(ENTRIES, json=operation_body(world, line(product, "3", unit_cost="1100")))
    assert operator.post(f"{ENTRIES}/{entry.json()['id']}/reversal", json=reversal_body(world)).status_code == 201
    clerk = as_user("inventario.test")
    adjustments = f"/api/v1/companies/{world.company}/inventory-adjustments"
    assert clerk.post(adjustments, json=adjustment(world, product, "POSITIVE", "2")).status_code == 201
    assert clerk.post(adjustments, json=adjustment(world, product, "NEGATIVE", "1")).status_code == 201
    return {"product": product, "other": other, "middle": middle, "end": datetime.now(UTC) + timedelta(seconds=1)}


def test_sums_by_type_identity_and_opening(as_user, world, history) -> None:
    start = history["middle"] - timedelta(microseconds=1)
    response = as_user("inventario.test").get(url(world), params=window(start, history["end"]))
    assert response.status_code == 200, response.text
    body = response.json()
    rows = {row["company_product_id"]: row for row in body["items"]}
    row = rows[str(history["product"])]
    assert {name: row[name] for name in FIELDS} == {
        "opening_quantity": "0.0000", "entries": "13.0000", "outputs": "4.0000", "entry_reversals": "3.0000",
        "output_reversals": "4.0000", "positive_adjustments": "2.0000", "negative_adjustments": "1.0000",
        "closing_quantity": "11.0000",
    }
    assert row["movement_count"] == 6
    # El producto 1 no tuvo movimientos en el período pero conserva su saldo: inicial = final = 5.
    other = rows[str(history["other"])]
    assert (other["opening_quantity"], other["closing_quantity"], other["movement_count"]) == ("5.0000", "5.0000", 0)
    for item in body["items"]:
        values = {name: Decimal(item[name]) for name in FIELDS}
        assert values["closing_quantity"] == (
            values["opening_quantity"] + values["entries"] - values["outputs"] - values["entry_reversals"]
            + values["output_reversals"] + values["positive_adjustments"] - values["negative_adjustments"]
        )
    assert set(body) == {"company_id", "branch_id", "from", "to", "items", "page", "page_size", "total_records",
                         "total_pages"}


def test_never_returns_costs(as_user, world, history) -> None:
    response = as_user("reportes.test").get(url(world), params=window(history["middle"], history["end"]))
    assert response.status_code == 200, response.text
    keys = {key for item in response.json()["items"] for key in item}
    assert not keys & COST_KEYS
    assert "1000" not in response.text and "1100" not in response.text  # ningún costo unitario aparece


def test_reportes_cannot_read_the_kardex_or_valuation(as_user, world, history) -> None:
    """DR-11: `stock_evolution:read` no abre el kardex, las operaciones ni la valoración."""
    reportes = as_user("reportes.test")
    base = f"/api/v1/companies/{world.company}"
    assert reportes.get(f"{base}/branches/{world.branch}/kardex/{history['product']}").status_code == 403
    assert reportes.get(f"{base}/branches/{world.branch}/valuation").status_code == 403
    assert reportes.get(f"{base}/branches/{world.branch}/balances").status_code == 403


def test_permission_and_isolation(as_user, as_token, make_token, world, history) -> None:
    params = window(history["middle"], history["end"])
    kardex_only = as_token(make_token("perm:inventory:movements:read", sub="solo-kardex-" + uuid4().hex))
    assert kardex_only.get(url(world), params=params).status_code == 403  # el permiso es propio
    assert as_user("compras.test").get(url(world), params=params).status_code == 403
    other_company = as_user("inventario.test").get(url(world, company=uuid4()), params=params)
    assert other_company.status_code == 404
    empty = as_user("inventario.test").get(url(world, branch=uuid4()), params=params).json()
    assert empty["items"] == [] and empty["total_records"] == 0  # sucursal ajena: ninguna fila de esta empresa


def test_product_filter_pagination_and_validation(as_user, world, history) -> None:
    client = as_user("inventario.test")
    params = window(history["middle"] - timedelta(days=1), history["end"])
    only = client.get(url(world), params={**params, "company_product_id": str(history["product"])}).json()
    assert [row["company_product_id"] for row in only["items"]] == [str(history["product"])]
    page = client.get(url(world), params={**params, "page_size": 1}).json()
    assert (len(page["items"]), page["total_records"], page["total_pages"]) == (1, 2, 2)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    assert client.get(url(world), params=window(start, start + timedelta(days=367))).status_code == 422
    assert client.get(url(world), params=window(start, start)).status_code == 422
    assert client.get(url(world), params={"from": "2026-01-01T00:00:00", "to": "2026-01-02T00:00:00"}).status_code == 422
    assert client.get(url(world), params={**params, "desconocido": "x"}).status_code == 422


def test_reportes_user_has_the_new_permission() -> None:
    from tests.conftest import USER_ROLES

    assert STOCK_EVOLUTION_READ in USER_ROLES["reportes.test"]
    assert "perm:inventory:movements:read" not in USER_ROLES["reportes.test"]


# --------------------------------------------------------------------------- INV-R1C (consolidada)


def consolidated_url(world, company=None) -> str:
    return f"/api/v1/companies/{company or world.company}/stock-evolution"


def test_consolidated_sums_each_branch_by_product(operator, as_user, world, history) -> None:
    """Producto 0 con movimientos en la sucursal principal y 4 unidades en la sucursal B: se suman por producto."""
    product = history["product"]
    branch_b = world.other_branch
    assert operator.post(ENTRIES, json=operation_body(world, line(product, "4", unit_cost="1000"),
                                                      branch_id=str(branch_b))).status_code == 201
    client = as_user("inventario.test")
    params = {**window(history["middle"] - timedelta(microseconds=1), datetime.now(UTC) + timedelta(seconds=1))}
    single = client.get(url(world), params=params).json()
    other = client.get(url(world, branch=branch_b), params=params).json()
    both = client.get(consolidated_url(world), params={**params, "branch_id": [str(world.branch), str(branch_b)]})
    assert both.status_code == 200, both.text
    rows = {row["company_product_id"]: row for row in both.json()["items"]}
    one = {row["company_product_id"]: row for row in single["items"]}[str(product)]
    two = {row["company_product_id"]: row for row in other["items"]}[str(product)]
    for name in FIELDS:
        assert Decimal(rows[str(product)][name]) == Decimal(one[name]) + Decimal(two[name]), name
    assert rows[str(product)]["branch_count"] == 2
    assert not {key for item in both.json()["items"] for key in item} & COST_KEYS


def test_consolidated_requires_branches_and_permission(as_user, as_token, make_token, world, history) -> None:
    params = window(history["middle"], history["end"])
    client = as_user("inventario.test")
    assert client.get(consolidated_url(world), params=params).status_code == 422  # branch_id obligatorio
    assert client.get(consolidated_url(world), params={**params, "branch_id": "no-uuid"}).status_code == 422
    kardex_only = as_token(make_token("perm:inventory:movements:read", sub="solo-kardex-" + uuid4().hex))
    assert kardex_only.get(consolidated_url(world), params={**params, "branch_id": str(world.branch)}).status_code == 403
    assert client.get(consolidated_url(world, company=uuid4()),
                      params={**params, "branch_id": str(world.branch)}).status_code == 404
    foreign = client.get(consolidated_url(world), params={**params, "branch_id": str(world.other_company_branch)}).json()
    assert foreign["items"] == [] and foreign["total_records"] == 0


def test_single_branch_route_does_not_expose_branch_count(as_user, world, history) -> None:
    body = as_user("inventario.test").get(url(world), params=window(history["middle"], history["end"])).json()
    assert all("branch_count" not in item for item in body["items"])
