"""Evolución de existencias consolidada de la empresa (ruta general de R4, sobre INV-R1C)."""

from __future__ import annotations

import csv
import io
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from tests.api.support import PERIOD, base
from tests.fakes import D, TABLET, StockEvolution

FIELDS = ("opening_quantity", "entries", "outputs", "entry_reversals", "output_reversals", "positive_adjustments",
          "negative_adjustments", "closing_quantity")


@pytest.fixture
def stocked(fakes):
    principal, norte, closed = (b.id for b in fakes.branches)
    shared = fakes.product("Producto en dos sucursales", code="P-2S", unit=TABLET)
    only_norte = fakes.product("Producto solo en Norte", code="P-N", unit=TABLET)
    in_closed = fakes.product("Producto en la sucursal cerrada", code="P-C", unit=TABLET)
    fakes.evolution[principal] = [StockEvolution(shared, D("10"), D("5"), D("3"), D("0"), D("1"), D("2"), D("1"), D("14"), 6)]
    fakes.evolution[norte] = [StockEvolution(shared, D("4"), D("2"), D("1"), D("0"), D("0"), D("0"), D("0"), D("5"), 2),
                              StockEvolution(only_norte, D("0"), D("7"), D("2"), D("0"), D("0"), D("0"), D("0"), D("5"), 2)]
    fakes.evolution[closed] = [StockEvolution(in_closed, D("3"), D("0"), D("0"), D("0"), D("0"), D("0"), D("0"), D("3"), 0)]
    return {"shared": shared, "only_norte": only_norte, "in_closed": in_closed}


def url(fakes) -> str:
    return f"{base(fakes)}/stock-evolution"


def test_consolidates_by_product_over_all_company_branches(as_user, fakes, stocked) -> None:
    response = as_user("reportes.test").get(url(fakes), params=PERIOD)
    assert response.status_code == 200, response.text
    body = response.json()
    rows = {row["company_product_id"]: row for row in body["items"]}
    shared = rows[str(stocked["shared"])]
    assert {name: shared[name] for name in FIELDS} == {
        "opening_quantity": "14.0000", "entries": "7.0000", "outputs": "4.0000", "entry_reversals": "0.0000",
        "output_reversals": "1.0000", "positive_adjustments": "2.0000", "negative_adjustments": "1.0000",
        "closing_quantity": "19.0000"}
    assert shared["branch_count"] == 2 and rows[str(stocked["only_norte"])]["branch_count"] == 1
    assert str(stocked["in_closed"]) in rows  # la sucursal inactiva conserva existencias y cuenta
    assert set(body["branch_ids"]) == {str(b.id) for b in fakes.branches}
    assert body["timezone"] == "America/Bogota" and body["total_records"] == 3
    assert not {"unit_cost", "movement_value", "cost_known", "inventory_value"} & {k for i in body["items"] for k in i}
    [call] = [args for name, args in fakes.log.calls if name == "consolidated_stock_evolution"]
    assert set(call["branch_ids"]) == {b.id for b in fakes.branches}
    assert fakes.log.count("stock_evolution") == 0  # una consulta consolidada, nunca una por sucursal
    assert fakes.log.count("company_products_search") == 1 and fakes.log.count("product_summaries") == 1


def test_branch_filter_equals_the_branch_route(as_user, fakes, stocked) -> None:
    client = as_user("reportes.test")
    norte = fakes.branches[1].id
    consolidated = client.get(url(fakes), params={**PERIOD, "branch_id": str(norte)}).json()
    single = client.get(f"/api/v1/companies/{fakes.company.id}/branches/{norte}/reports/stock-evolution",
                        params=PERIOD).json()
    strip = lambda items: [{k: v for k, v in i.items() if k != "branch_count"} for i in items]  # noqa: E731
    assert strip(consolidated["items"]) == single["items"]
    assert all(i["branch_count"] == 1 for i in consolidated["items"])
    assert all("branch_count" not in i for i in single["items"])  # la ruta por sucursal no cambia


def test_identity_failure_is_503(as_user, fakes, stocked) -> None:
    principal = fakes.branches[0].id
    fakes.evolution[principal] = [replace(fakes.evolution[principal][0], closing_quantity=Decimal("99"))]
    assert as_user("reportes.test").get(url(fakes), params=PERIOD).status_code == 503


def test_isolation_and_permissions(as_user, fakes, stocked) -> None:
    client = as_user("reportes.test")
    assert client.get(url(fakes), params={**PERIOD, "branch_id": str(uuid4())}).status_code == 404
    assert client.get(f"/api/v1/companies/{uuid4()}/reports/stock-evolution", params=PERIOD).status_code == 404
    for name, expected in (("inventario.test", 200), ("ventas.test", 403), ("compras.test", 403),
                           ("consulta.test", 403), ("admin.test", 200), ("supervisor.test", 200)):
        assert as_user(name).get(url(fakes), params=PERIOD).status_code == expected, name


def test_pagination_and_product_filter(as_user, fakes, stocked) -> None:
    client = as_user("reportes.test")
    first = client.get(url(fakes), params={**PERIOD, "page_size": 2}).json()
    second = client.get(url(fakes), params={**PERIOD, "page_size": 2, "page": 2}).json()
    assert (len(first["items"]), len(second["items"]), first["total_pages"]) == (2, 1, 2)
    only = client.get(url(fakes), params={**PERIOD, "company_product_id": str(stocked["only_norte"])}).json()
    assert [i["company_product_id"] for i in only["items"]] == [str(stocked["only_norte"])]


def test_csv_matches_json_with_branch_count(as_user, fakes, stocked) -> None:
    client = as_user("reportes.test")
    data = client.get(url(fakes), params=PERIOD).json()
    response = client.get(url(fakes), params={**PERIOD, "format": "csv"})
    rows = list(csv.reader(io.StringIO(response.text[1:])))
    assert rows[0][-3:] == ["Movimientos", "Sucursales", "ID producto"]
    assert rows[-1] == ["TOTAL FILAS", "3"]
    assert [[r[10], r[12], r[13]] for r in rows[1:4]] == [
        [i["closing_quantity"], str(i["branch_count"]), i["company_product_id"]] for i in data["items"]]
