"""Los cuatro reportes en JSON con dobles (spec 023, FR-023-20 a FR-023-33)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from tests.api.support import PERIOD, base, branch_base, seed_evolution, seed_purchases, seed_sales
from tests.fakes import D


def test_top_products_default_rank_by_quantity_with_units_and_mixed_flag(as_user, fakes) -> None:
    tablets, syrup = seed_sales(fakes)
    response = as_user("reportes.test").get(f"{base(fakes)}/top-selling-products", params=PERIOD)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["company_product_id"] for item in body["items"]] == [str(syrup), str(tablets)]  # 2400 > 1250
    assert [item["rank"] for item in body["items"]] == [1, 2]
    assert body["items"][0]["base_unit"]["code"] == "ML" and body["items"][1]["base_unit"]["code"] == "TAB"
    assert body["mixed_base_units"] is True
    assert body["criteria"] == {"sales_status": "CONFIRMED", "date_basis": "operation_date", "rank_by": "quantity"}
    assert body["totals"] == [{"currency_code": "COP", "amount": "1025000.00", "sales_count": 95}]
    assert "quantity" not in str(body["totals"])  # nunca se suman cantidades de productos distintos
    [call] = [args for name, args in fakes.log.calls if name == "sales_by_product"]
    assert call["order_by"] == "quantity_base" and call["branch_ids"] == []


def test_top_products_by_amount_with_presentations_and_one_branch(as_user, fakes) -> None:
    tablets, _ = seed_sales(fakes)
    branch = fakes.branches[0].id
    response = as_user("ventas.test").get(f"{base(fakes)}/top-selling-products", params={
        **PERIOD, "rank_by": "amount", "include_presentations": "true", "branch_id": str(branch), "limit": 1})
    body = response.json()
    assert response.status_code == 200, response.text
    assert [item["company_product_id"] for item in body["items"]] == [str(tablets)]
    assert body["mixed_base_units"] is False
    assert [p["quantity_base"] for p in body["items"][0]["presentations"]] == ["1000.0000", "250.0000"]
    [call] = [args for name, args in fakes.log.calls if name == "sales_by_product"]
    assert call == {**call, "order_by": "amount", "limit": 1, "include_presentations": True, "branch_ids": [branch]}


def test_one_batch_to_cr_and_pc_per_report(as_user, fakes) -> None:
    seed_sales(fakes)
    as_user("reportes.test").get(f"{base(fakes)}/top-selling-products", params=PERIOD)
    assert fakes.log.count("company_products_search") == 1 and fakes.log.count("product_summaries") == 1
    assert fakes.log.names()[:3].count("operational_access") == 1  # OC antes que cualquier propietario
    assert fakes.log.names().index("sales_by_product") > fakes.log.names().index("operational_access")


def test_sales_by_branch_fills_zero_branches_and_share(as_user, fakes) -> None:
    seed_sales(fakes)
    body = as_user("reportes.test").get(f"{base(fakes)}/sales-by-branch", params=PERIOD).json()
    rows = {row["branch_code"]: row for row in body["items"]}
    assert set(rows) == {"PPAL", "NORTE"}  # la inactiva sin ventas no aparece en el alcance de la empresa
    assert (rows["PPAL"]["total_amount"], rows["PPAL"]["share_percentage"]) == ("750000.00", "75.0000")
    assert (rows["NORTE"]["sales_count"], rows["NORTE"]["share_percentage"]) == (35, "25.0000")
    assert body["totals"] == [{"currency_code": "COP", "sales_count": 95, "total_amount": "1000000.00"}]


def test_sales_by_branch_without_sales_has_zero_rows_in_company_currency(as_user, fakes) -> None:
    body = as_user("reportes.test").get(f"{base(fakes)}/sales-by-branch", params=PERIOD).json()
    assert {(r["branch_code"], r["sales_count"], r["total_amount"], r["share_percentage"]) for r in body["items"]} == {
        ("PPAL", 0, "0.00", "0.0000"), ("NORTE", 0, "0.00", "0.0000")}
    assert body["totals"] == [{"currency_code": "COP", "sales_count": 0, "total_amount": "0.00"}]


def test_sales_of_a_branch_outside_the_company_is_an_integrity_incident(as_user, fakes) -> None:
    from uuid import uuid4

    from business_reporting_service.application.ports import BranchSales

    fakes.branch_sales = [BranchSales(uuid4(), "COP", 1, D("10"))]
    response = as_user("reportes.test").get(f"{base(fakes)}/sales-by-branch", params=PERIOD)
    assert response.status_code == 503 and response.json()["code"] == "BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE"


def test_purchases_categories_and_period_totals(as_user, fakes) -> None:
    seed_purchases(fakes, 3)
    response = as_user("compras.test").get(f"{base(fakes)}/purchases", params=PERIOD)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["category"] for item in body["items"]] == ["RECEIVED", "PENDING_RECEIPT", "CANCELLED"]
    assert body["items"][0]["branch_name"] == "Principal" and body["items"][1]["received_at"] is None
    assert body["totals"][0]["effective_total"] == "2000.00" and body["totals"][0]["cancelled_total"] == "1000.00"
    assert (body["total_records"], body["total_pages"]) == (3, 1)
    filtered = as_user("compras.test").get(f"{base(fakes)}/purchases",
                                           params={**PERIOD, "category": "PENDING_RECEIPT"}).json()
    assert [item["category"] for item in filtered["items"]] == ["PENDING_RECEIPT"]
    assert filtered["totals"] == body["totals"]  # los totales son del período completo


def test_stock_evolution_branch_in_path_with_timezone_window(as_user, fakes) -> None:
    rows = seed_evolution(fakes, 2)
    branch = fakes.branches[0]
    response = as_user("inventario.test").get(f"{branch_base(fakes)}/stock-evolution", params=PERIOD)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["branch_id"], body["branch_code"], body["timezone"]) == (str(branch.id), "PPAL", "America/Bogota")
    assert body["criteria"]["from"] == "2026-10-01T00:00:00-05:00" and body["criteria"]["to"] == "2026-10-19T00:00:00-05:00"
    first = body["items"][0]
    assert (first["opening_quantity"], first["closing_quantity"], first["base_unit"]["code"]) == ("10.0000", "14.0000", "TAB")
    assert {item["product_name"] for item in body["items"]} == {"Producto ficticio 000", "Producto ficticio 001"}
    assert [item["company_product_id"] for item in body["items"]] == sorted(str(r.company_product_id) for r in rows)
    assert not {"unit_cost", "movement_value", "cost_known", "inventory_value"} & set(first)
    assert len(body["items"]) == len(rows)


def test_stock_evolution_identity_failure_is_503(as_user, fakes) -> None:
    [row] = seed_evolution(fakes, 1)
    fakes.evolution[fakes.branches[0].id] = [replace(row, closing_quantity=Decimal("99"))]
    response = as_user("inventario.test").get(f"{branch_base(fakes)}/stock-evolution", params=PERIOD)
    assert response.status_code == 503


def test_stock_evolution_unknown_product_in_cr_is_503(as_user, fakes) -> None:
    [row] = seed_evolution(fakes, 1)
    fakes.products.pop(row.company_product_id)
    assert as_user("inventario.test").get(f"{branch_base(fakes)}/stock-evolution", params=PERIOD).status_code == 503
