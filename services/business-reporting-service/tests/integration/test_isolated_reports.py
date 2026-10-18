"""Los cuatro reportes con servicios reales en `sio-it` (spec 023, fase 1). **Solo `GET`**: no crea ni modifica datos.

Cada reporte se compara con un oráculo obtenido por otro camino: las agregaciones de los propietarios consultadas
directamente (SAL-R1, SAL-R2, PUR-R1, INV-R1) y las API de listado y kardex. La matriz de permisos usa tokens reales
y la membresía real de cada usuario (`me/operational-context`).
"""

from __future__ import annotations

import csv
import io
import uuid
from collections import defaultdict
from decimal import Decimal

import pytest

from tests.integration.scenario import PERIOD, PURCHASE_COMPANY, SALES_COMPANY, VOLUME_COMPANY
from tests.integration.support import BRS, INVENTORY, OC, PURCHASE, SALES

pytestmark = pytest.mark.integration

USERS = ("admin.test", "supervisor.test", "ventas.test", "compras.test", "inventario.test", "reportes.test",
         "consulta.test")
# Permisos del reporte + del propietario (plantilla del realm): quién puede cada reporte si es miembro.
CAN = {
    "top-selling-products": {"admin.test", "supervisor.test", "ventas.test", "reportes.test"},
    "sales-by-branch": {"admin.test", "supervisor.test", "reportes.test"},
    "purchases": {"admin.test", "supervisor.test", "compras.test", "reportes.test"},
    "stock-evolution": {"admin.test", "supervisor.test", "inventario.test", "reportes.test"},
}
QUANTITIES = ("opening_quantity", "entries", "outputs", "entry_reversals", "output_reversals", "positive_adjustments",
              "negative_adjustments", "closing_quantity")
COST_KEYS = {"unit_cost", "movement_value", "cost_known", "inventory_value", "average_unit_cost", "cost"}


def ok(response):
    assert response.status_code == 200, (response.status_code, response.text[:300])
    return response


def csv_rows(response) -> list[list[str]]:
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.text.startswith("﻿")
    rows = list(csv.reader(io.StringIO(response.text[1:])))
    assert rows[-1][0] == "TOTAL FILAS", "CSV incompleto"
    return rows


@pytest.fixture(scope="module")
def memberships(users) -> dict[str, set[str]]:
    result = {}
    for name in USERS:
        body = ok(users(name).get(f"{OC}/me/operational-context")).json()
        result[name] = {m["company_id"] for m in body["memberships"] if m["status"] == "ACTIVE"}
    return result


@pytest.fixture(scope="module")
def branches(users) -> dict[str, list[dict]]:
    found = {}
    for company in (SALES_COMPANY, PURCHASE_COMPANY, VOLUME_COMPANY):
        found[company] = ok(users("admin.test").get(f"{OC}/companies/{company}/branches",
                                                     params={"page_size": 100})).json()["items"]
    return found


def report_url(report: str, company: str, branch: str | None = None) -> str:
    if report == "stock-evolution":
        return f"{BRS}/companies/{company}/branches/{branch}/reports/stock-evolution"
    return f"{BRS}/companies/{company}/reports/{report}"


def sales_branch(users) -> str:
    rows = ok(users("admin.test").get(f"{SALES}/companies/{SALES_COMPANY}/sales-aggregates/by-branch",
                                      params=PERIOD)).json()["items"]
    return rows[0]["branch_id"]


# --------------------------------------------------------------------------- permisos y aislamiento


def test_matrix_per_group_with_real_tokens_and_real_memberships(users, memberships, branches) -> None:
    branch = branches[SALES_COMPANY][0]["id"]
    targets = {"top-selling-products": SALES_COMPANY, "sales-by-branch": SALES_COMPANY,
               "purchases": PURCHASE_COMPANY, "stock-evolution": SALES_COMPANY}
    checked = 0
    for name in USERS:
        for report, company in targets.items():
            response = users(name).get(report_url(report, company, branch), params=PERIOD)
            expected = 403 if name not in CAN[report] else (200 if company in memberships[name] else 404)
            assert response.status_code == expected, (name, report, response.status_code, response.text[:200])
            if expected == 403:
                assert "perm:" not in response.text
            checked += 1
    assert checked == len(USERS) * 4


def test_other_company_and_foreign_branch_are_404(users, branches) -> None:
    reportes = users("reportes.test")
    assert reportes.get(report_url("top-selling-products", str(uuid.uuid4())), params=PERIOD).status_code == 404
    foreign = branches[PURCHASE_COMPANY][0]["id"]
    assert reportes.get(report_url("stock-evolution", SALES_COMPANY, foreign), params=PERIOD).status_code == 404
    assert reportes.get(report_url("sales-by-branch", SALES_COMPANY), params={**PERIOD, "branch_id": foreign}).status_code == 404
    assert reportes.get(report_url("stock-evolution", SALES_COMPANY, branches[SALES_COMPANY][0]["id"]),
                        params={**PERIOD, "branch_id": foreign}).status_code == 422


def test_owner_permissions_are_enforced_with_the_user_token(users, branches) -> None:
    """DR-07 y DR-11: los propietarios aplican sus permisos al token del usuario."""
    branch = branches[SALES_COMPANY][0]["id"]
    assert users("compras.test").get(f"{SALES}/companies/{PURCHASE_COMPANY}/sales-aggregates/by-product",
                                     params=PERIOD).status_code == 403
    assert users("ventas.test").get(f"{PURCHASE}/companies/{SALES_COMPANY}/purchase-reports/period",
                                    params=PERIOD).status_code == 403
    reportes = users("reportes.test")
    assert reportes.get(f"{INVENTORY}/companies/{SALES_COMPANY}/branches/{branch}/kardex/{uuid.uuid4()}").status_code == 403
    assert reportes.get(f"{INVENTORY}/companies/{SALES_COMPANY}/branches/{branch}/valuation").status_code == 403
    window = {"from": "2026-10-01T00:00:00-05:00", "to": "2026-10-19T00:00:00-05:00"}
    evolution = ok(reportes.get(f"{INVENTORY}/companies/{SALES_COMPANY}/branches/{branch}/stock-evolution",
                                params=window)).json()
    assert not COST_KEYS & {key for item in evolution["items"] for key in item}


# --------------------------------------------------------------------------- R1 y R2


def confirmed_sales_oracle(users) -> tuple[Decimal, int, set[str]]:
    """Oráculo independiente: el listado de ventas `CONFIRMED` de Sales (y que hay anuladas que no deben contar)."""
    client = users("admin.test")
    total, count, page = Decimal("0"), 0, 1
    while True:
        body = ok(client.get(f"{SALES}/companies/{SALES_COMPANY}/sales", params={
            "status": "CONFIRMED", "operation_date_from": PERIOD["date_from"], "operation_date_to": PERIOD["date_to"],
            "page": page, "page_size": 100})).json()
        for sale in body["items"]:
            total += Decimal(sale["subtotal"]) - Decimal(sale["discount_total"])
            count += 1
        if page >= body["total_pages"]:
            break
        page += 1
    cancelled = ok(client.get(f"{SALES}/companies/{SALES_COMPANY}/sales", params={
        "status": "CANCELLED", "operation_date_from": PERIOD["date_from"], "operation_date_to": PERIOD["date_to"]})).json()
    return total, count, {sale["id"] for sale in cancelled["items"]}


def test_r1_top_selling_products_against_sales(users) -> None:
    reportes = users("reportes.test")
    report = ok(reportes.get(report_url("top-selling-products", SALES_COMPANY), params=PERIOD)).json()
    direct = ok(reportes.get(f"{SALES}/companies/{SALES_COMPANY}/sales-aggregates/by-product", params=PERIOD)).json()
    assert [i["company_product_id"] for i in report["items"]] == [i["company_product_id"] for i in direct["items"]]
    assert [(i["quantity_base"], i["amount"]) for i in report["items"]] == [
        (i["quantity_base"], i["amount"]) for i in direct["items"]]
    quantities = [Decimal(i["quantity_base"]) for i in report["items"]]
    assert quantities == sorted(quantities, reverse=True)  # orden por cantidad (DR-04)
    assert all(i["base_unit"] for i in report["items"]) and report["mixed_base_units"] is False
    total, count, cancelled = confirmed_sales_oracle(users)
    assert cancelled, "el escenario debe tener ventas anuladas"
    assert report["totals"] == [{"currency_code": "COP", "amount": f"{total:.2f}", "sales_count": count}]
    by_amount = ok(reportes.get(report_url("top-selling-products", SALES_COMPANY),
                                params={**PERIOD, "rank_by": "amount", "limit": 1, "include_presentations": "true"})).json()
    assert len(by_amount["items"]) == 1 and by_amount["items"][0]["presentations"]
    assert by_amount["items"][0]["amount"] == max((i["amount"] for i in report["items"]), key=Decimal)


def test_r2_sales_by_branch_against_sales(users, branches) -> None:
    reportes = users("reportes.test")
    report = ok(reportes.get(report_url("sales-by-branch", SALES_COMPANY), params=PERIOD)).json()
    active = {b["id"] for b in branches[SALES_COMPANY] if b["status"] == "ACTIVE"}
    assert {i["branch_id"] for i in report["items"]} == active  # todas, también las que no venden
    direct = {r["branch_id"]: r for r in ok(reportes.get(
        f"{SALES}/companies/{SALES_COMPANY}/sales-aggregates/by-branch", params=PERIOD)).json()["items"]}
    for item in report["items"]:
        expected = direct.get(item["branch_id"], {"sales_count": 0, "total_amount": "0.00"})
        assert (item["sales_count"], item["total_amount"]) == (expected["sales_count"], expected["total_amount"])
    assert sum(Decimal(i["share_percentage"]) for i in report["items"]) == Decimal("100.0000")
    total, count, _ = confirmed_sales_oracle(users)
    assert report["totals"] == [{"currency_code": "COP", "sales_count": count, "total_amount": f"{total:.2f}"}]
    one = sales_branch(users)
    filtered = ok(reportes.get(report_url("sales-by-branch", SALES_COMPANY), params={**PERIOD, "branch_id": one})).json()
    assert [i["branch_id"] for i in filtered["items"]] == [one]


# --------------------------------------------------------------------------- R3


def purchases_oracle(users) -> dict:
    client = users("admin.test")
    sums, counts = defaultdict(Decimal), defaultdict(int)
    page = 1
    while True:
        body = ok(client.get(f"{PURCHASE}/companies/{PURCHASE_COMPANY}/purchases", params={
            "operation_date_from": PERIOD["date_from"], "operation_date_to": PERIOD["date_to"], "page": page,
            "page_size": 100})).json()
        for p in body["items"]:
            if p["status"] == "DRAFT":
                continue
            category = "CANCELLED" if p["status"] == "CANCELLED" else ("RECEIVED" if p["received_at"] else "PENDING_RECEIPT")
            sums[category] += Decimal(p["total"])
            counts[category] += 1
        if page >= body["total_pages"]:
            break
        page += 1
    return {"sums": sums, "counts": counts}


def test_r3_purchases_classification_totals_filters_and_pages(users) -> None:
    reportes = users("reportes.test")
    report = ok(reportes.get(report_url("purchases", PURCHASE_COMPANY), params=PERIOD)).json()
    oracle = purchases_oracle(users)
    [totals] = report["totals"]
    assert (totals["received_count"], totals["pending_receipt_count"], totals["cancelled_count"]) == (
        oracle["counts"]["RECEIVED"], oracle["counts"]["PENDING_RECEIPT"], oracle["counts"]["CANCELLED"])
    assert Decimal(totals["received_total"]) == oracle["sums"]["RECEIVED"]
    assert Decimal(totals["effective_total"]) == oracle["sums"]["RECEIVED"] + oracle["sums"]["PENDING_RECEIPT"]
    assert Decimal(totals["cancelled_total"]) == oracle["sums"]["CANCELLED"]  # informado, no suma
    assert report["total_records"] == sum(oracle["counts"].values())  # sin borradores
    assert all(i["status"] != "DRAFT" for i in report["items"])
    assert all(i["received_at"] is None for i in report["items"] if i["category"] == "PENDING_RECEIPT")
    direct = ok(reportes.get(f"{PURCHASE}/companies/{PURCHASE_COMPANY}/purchase-reports/period", params=PERIOD)).json()
    assert direct["totals"] == report["totals"]
    pending = ok(reportes.get(report_url("purchases", PURCHASE_COMPANY),
                              params={**PERIOD, "category": "PENDING_RECEIPT"})).json()
    assert {i["category"] for i in pending["items"]} == {"PENDING_RECEIPT"} and pending["totals"] == report["totals"]
    seen, page = [], 1
    while True:
        body = ok(reportes.get(report_url("purchases", PURCHASE_COMPANY), params={**PERIOD, "page_size": 4,
                                                                                   "page": page})).json()
        seen += [i["purchase_id"] for i in body["items"]]
        if page >= body["total_pages"]:
            break
        page += 1
    assert len(seen) == len(set(seen)) == report["total_records"]


# --------------------------------------------------------------------------- R4


def kardex_oracle(users, company: str, branch: str, product: str) -> dict:
    """Sumas por tipo desde el kardex (con `admin.test`, que sí puede leerlo)."""
    body = ok(users("admin.test").get(f"{INVENTORY}/companies/{company}/branches/{branch}/kardex/{product}",
                                      params={"page_size": 100})).json()
    sums = defaultdict(Decimal)
    for movement in body["items"]:
        if PERIOD["date_from"] <= movement["created_at"][:10] <= PERIOD["date_to"]:
            sums[movement["movement_type"]] += Decimal(movement["quantity"])
    return sums


def test_r4_stock_evolution_against_inventory_and_kardex(users, branches) -> None:
    branch = sales_branch(users)
    reportes = users("reportes.test")
    report = ok(reportes.get(report_url("stock-evolution", SALES_COMPANY, branch), params=PERIOD)).json()
    assert report["items"] and report["branch_id"] == branch
    for item in report["items"]:
        assert not COST_KEYS & set(item)
        v = {k: Decimal(item[k]) for k in QUANTITIES}
        assert v["closing_quantity"] == (v["opening_quantity"] + v["entries"] - v["outputs"] - v["entry_reversals"]
                                         + v["output_reversals"] + v["positive_adjustments"] - v["negative_adjustments"])
        sums = kardex_oracle(users, SALES_COMPANY, branch, item["company_product_id"])
        assert Decimal(item["entries"]) == sums["PURCHASE_ENTRY"] and Decimal(item["outputs"]) == sums["SALE_OUTPUT"]
        assert Decimal(item["output_reversals"]) == sums["OUTPUT_REVERSAL"]
        assert Decimal(item["entry_reversals"]) == sums["ENTRY_REVERSAL"]
    assert any(Decimal(i["output_reversals"]) > 0 for i in report["items"])  # el escenario tiene reversos


def test_r4_pagination_on_volume_company(users, branches) -> None:
    branch = branches[VOLUME_COMPANY][0]["id"]
    client = users("inventario.test")
    first = ok(client.get(report_url("stock-evolution", VOLUME_COMPANY, branch), params={**PERIOD, "page_size": 100})).json()
    assert first["total_records"] > 100, "el juego de volumen debe tener más de una página"
    second = ok(client.get(report_url("stock-evolution", VOLUME_COMPANY, branch),
                           params={**PERIOD, "page_size": 100, "page": 2})).json()
    assert {i["company_product_id"] for i in first["items"]}.isdisjoint({i["company_product_id"] for i in second["items"]})
    one = first["items"][0]["company_product_id"]
    only = ok(client.get(report_url("stock-evolution", VOLUME_COMPANY, branch),
                         params={**PERIOD, "company_product_id": one})).json()
    assert [i["company_product_id"] for i in only["items"]] == [one]


# --------------------------------------------------------------------------- CSV


@pytest.mark.parametrize("report", ["top-selling-products", "sales-by-branch", "purchases", "stock-evolution"])
def test_csv_matches_json(users, report) -> None:
    company = PURCHASE_COMPANY if report == "purchases" else SALES_COMPANY
    branch = sales_branch(users) if report == "stock-evolution" else None
    client = users("reportes.test")
    paged = {"page_size": 100} if report in ("purchases", "stock-evolution") else {}  # R1 y R2 no paginan (422)
    data = ok(client.get(report_url(report, company, branch), params={**PERIOD, **paged})).json()
    rows = csv_rows(ok(client.get(report_url(report, company, branch), params={**PERIOD, "format": "csv"})))
    count = int(rows[-1][1])
    assert count == data.get("total_records", len(data["items"]))
    body = rows[1:1 + count]
    ids = {"top-selling-products": "company_product_id", "sales-by-branch": "branch_id", "purchases": "purchase_id",
           "stock-evolution": "company_product_id"}[report]
    assert [row[-1] for row in body] == [item[ids] for item in data["items"]]
    amounts = {"top-selling-products": (5, "amount"), "sales-by-branch": (4, "total_amount"), "purchases": (10, "total"),
               "stock-evolution": (10, "closing_quantity")}[report]
    assert [row[amounts[0]] for row in body] == [item[amounts[1]] for item in data["items"]]


def test_csv_of_large_stock_evolution_is_complete(users, branches) -> None:
    branch = branches[VOLUME_COMPANY][0]["id"]
    client = users("inventario.test")
    data = ok(client.get(report_url("stock-evolution", VOLUME_COMPANY, branch), params={**PERIOD, "page_size": 1})).json()
    rows = csv_rows(ok(client.get(report_url("stock-evolution", VOLUME_COMPANY, branch), params={**PERIOD, "format": "csv"})))
    assert int(rows[-1][1]) == data["total_records"] == len(rows) - 2


# --------------------------------------------------------------------------- rutas por sucursal


def branch_report_url(report: str, company: str, branch: str) -> str:
    return f"{BRS}/companies/{company}/branches/{branch}/reports/{report}"


@pytest.mark.parametrize("report", ["top-selling-products", "purchases"])
def test_branch_routes_equal_company_route_with_branch_id(users, report) -> None:
    company = PURCHASE_COMPANY if report == "purchases" else SALES_COMPANY
    branch = sales_branch(users) if report != "purchases" else ok(users("admin.test").get(
        f"{PURCHASE}/companies/{PURCHASE_COMPANY}/purchase-reports/period", params=PERIOD)).json()["items"][0]["branch_id"]
    client = users("reportes.test")
    by_path = ok(client.get(branch_report_url(report, company, branch), params=PERIOD)).json()
    by_query = ok(client.get(report_url(report, company), params={**PERIOD, "branch_id": branch})).json()
    by_path.pop("generated_at"), by_query.pop("generated_at")
    assert by_path == by_query and by_path["items"]
    assert client.get(branch_report_url(report, company, branch),
                      params={**PERIOD, "branch_id": branch}).status_code == 422


def test_branch_sales_has_only_that_branch(users, branches) -> None:
    client = users("reportes.test")
    selling = sales_branch(users)
    body = ok(client.get(branch_report_url("sales-by-branch", SALES_COMPANY, selling), params=PERIOD)).json()
    direct = ok(client.get(f"{SALES}/companies/{SALES_COMPANY}/sales-aggregates/by-branch",
                           params={**PERIOD, "branch_id": selling})).json()["items"][0]
    assert body["branch_id"] == selling and "share_percentage" not in str(body)
    assert body["items"] == [{"currency_code": direct["currency_code"], "sales_count": direct["sales_count"],
                              "total_amount": direct["total_amount"]}]
    quiet = next((b["id"] for b in branches[SALES_COMPANY] if b["id"] != selling and b["status"] == "ACTIVE"), None)
    if quiet:
        zero = ok(client.get(branch_report_url("sales-by-branch", SALES_COMPANY, quiet), params=PERIOD)).json()
        assert [i["sales_count"] for i in zero["items"]] == [0]


# --------------------------------------------------------------------------- R4 consolidada (INV-R1C)


def test_r4_company_route_consolidates_the_branch_routes(users, branches) -> None:
    """Ruta de empresa = suma por producto de las rutas por sucursal (y = INV-R1C directo)."""
    client = users("inventario.test")
    company_rows = []
    page = 1
    while True:
        body = ok(client.get(f"{BRS}/companies/{VOLUME_COMPANY}/reports/stock-evolution",
                             params={**PERIOD, "page_size": 100, "page": page})).json()
        company_rows += body["items"]
        if page >= body["total_pages"]:
            break
        page += 1
    assert len(company_rows) == body["total_records"] and body["timezone"]
    expected: dict[str, dict] = defaultdict(lambda: defaultdict(Decimal))
    for branch in branches[VOLUME_COMPANY]:
        page = 1
        while True:
            part = ok(client.get(report_url("stock-evolution", VOLUME_COMPANY, branch["id"]),
                                 params={**PERIOD, "page_size": 100, "page": page})).json()
            for item in part["items"]:
                for name in QUANTITIES:
                    expected[item["company_product_id"]][name] += Decimal(item[name])
                expected[item["company_product_id"]]["branch_count"] += 1
            if page >= part["total_pages"]:
                break
            page += 1
    assert {row["company_product_id"] for row in company_rows} == set(expected)
    for row in company_rows:
        for name in QUANTITIES:
            assert Decimal(row[name]) == expected[row["company_product_id"]][name], (row["company_product_id"], name)
        assert row["branch_count"] == expected[row["company_product_id"]]["branch_count"]
        assert not COST_KEYS & set(row)
    window = {"from": body["criteria"]["from"], "to": body["criteria"]["to"], "page_size": 100}
    direct = ok(client.get(f"{INVENTORY}/companies/{VOLUME_COMPANY}/stock-evolution",
                           params={**window, "branch_id": body["branch_ids"]})).json()
    assert direct["total_records"] == body["total_records"]


def test_r4_company_route_with_branch_filter_and_csv(users, branches) -> None:
    client = users("reportes.test")
    branch = sales_branch(users)
    filtered = ok(client.get(f"{BRS}/companies/{SALES_COMPANY}/reports/stock-evolution",
                             params={**PERIOD, "branch_id": branch})).json()
    single = ok(client.get(report_url("stock-evolution", SALES_COMPANY, branch), params=PERIOD)).json()
    assert [{k: v for k, v in i.items() if k != "branch_count"} for i in filtered["items"]] == single["items"]
    rows = csv_rows(ok(client.get(f"{BRS}/companies/{SALES_COMPANY}/reports/stock-evolution",
                                  params={**PERIOD, "format": "csv"})))
    data = ok(client.get(f"{BRS}/companies/{SALES_COMPANY}/reports/stock-evolution",
                         params={**PERIOD, "page_size": 100})).json()
    assert int(rows[-1][1]) == data["total_records"]
    assert [r[-1] for r in rows[1:-1]] == [i["company_product_id"] for i in data["items"]]
    assert client.get(f"{BRS}/companies/{SALES_COMPANY}/reports/stock-evolution",
                      params={**PERIOD, "branch_id": branches[PURCHASE_COMPANY][0]["id"]}).status_code == 404
