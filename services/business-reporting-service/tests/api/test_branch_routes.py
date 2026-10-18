"""Rutas por sucursal de R1, R2 y R3 (ampliación de la spec 023): mismo caso de uso que la ruta de la empresa con un
único `branch_id`, solo la sucursal de la ruta, `branch_id` por consulta rechazado y aislamiento."""

from __future__ import annotations

import csv
import io
from uuid import uuid4

import pytest

from tests.api.support import PERIOD, base, seed_purchases, seed_sales
from tests.fakes import purchase

REPORTS = ("top-selling-products", "sales-by-branch", "purchases")
CAN = {"top-selling-products": {"admin.test", "supervisor.test", "ventas.test", "reportes.test"},
       "sales-by-branch": {"admin.test", "supervisor.test", "reportes.test"},
       "purchases": {"admin.test", "supervisor.test", "compras.test", "reportes.test"}}
USERS = ("admin.test", "supervisor.test", "ventas.test", "compras.test", "inventario.test", "reportes.test",
         "consulta.test")


def branch_url(fakes, report: str, branch=None) -> str:
    return f"/api/v1/companies/{fakes.company.id}/branches/{branch or fakes.branches[0].id}/reports/{report}"


def without_time(body: dict) -> dict:
    return {key: value for key, value in body.items() if key != "generated_at"}


@pytest.fixture
def seeded(fakes):
    seed_sales(fakes)
    seed_purchases(fakes)
    norte = fakes.branches[1].id
    fakes.purchases.append(purchase(norte, "RECEIVED", "500.00", number="OC-NORTE"))
    return fakes


@pytest.mark.parametrize("report", ["top-selling-products", "purchases"])
def test_same_result_as_the_company_route_with_one_branch_id(as_user, seeded, report) -> None:
    client = as_user("reportes.test")
    branch = seeded.branches[0].id
    by_path = client.get(branch_url(seeded, report), params=PERIOD)
    by_query = client.get(f"{base(seeded)}/{report}", params={**PERIOD, "branch_id": str(branch)})
    assert by_path.status_code == by_query.status_code == 200, by_path.text
    assert without_time(by_path.json()) == without_time(by_query.json())


def test_owner_receives_only_the_branch_of_the_path(as_user, seeded) -> None:
    branch = seeded.branches[1].id
    client = as_user("reportes.test")
    for report in REPORTS:
        assert client.get(branch_url(seeded, report, branch), params=PERIOD).status_code == 200
    for name in ("sales_by_product", "sales_by_branch", "purchase_period"):
        [call] = [args for op, args in seeded.log.calls if op == name]
        assert call["branch_ids"] == [branch], name


def test_purchases_of_the_branch_only(as_user, seeded) -> None:
    norte = seeded.branches[1].id
    body = as_user("compras.test").get(branch_url(seeded, "purchases", norte), params=PERIOD).json()
    assert [item["number"] for item in body["items"]] == ["OC-NORTE"]
    assert {item["branch_id"] for item in body["items"]} == {str(norte)}


def test_sales_of_one_branch_without_share_and_with_zero(as_user, seeded) -> None:
    client = as_user("reportes.test")
    principal = client.get(branch_url(seeded, "sales-by-branch"), params=PERIOD).json()
    assert principal["branch_code"] == "PPAL" and "share_percentage" not in str(principal)
    assert principal["items"] == [{"currency_code": "COP", "sales_count": 60, "total_amount": "750000.00"}]
    seeded.branch_sales = []  # la sucursal no vende: una fila en cero en la moneda de la empresa
    empty = client.get(branch_url(seeded, "sales-by-branch", seeded.branches[1].id), params=PERIOD).json()
    assert empty["items"] == [{"currency_code": "COP", "sales_count": 0, "total_amount": "0.00"}]


def test_company_route_share_is_over_the_branches_in_the_response(as_user, seeded) -> None:
    client = as_user("reportes.test")
    whole = client.get(f"{base(seeded)}/sales-by-branch", params=PERIOD).json()
    assert {i["branch_code"]: i["share_percentage"] for i in whole["items"]} == {"PPAL": "75.0000", "NORTE": "25.0000"}
    one = client.get(f"{base(seeded)}/sales-by-branch", params={**PERIOD, "branch_id": str(seeded.branches[1].id)}).json()
    assert [i["share_percentage"] for i in one["items"]] == ["100.0000"]  # sobre las sucursales filtradas


@pytest.mark.parametrize("report", REPORTS)
def test_query_branch_id_is_rejected_in_branch_routes(as_user, seeded, report) -> None:
    response = as_user("reportes.test").get(branch_url(seeded, report),
                                            params={**PERIOD, "branch_id": str(seeded.branches[1].id)})
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "UNKNOWN_FIELD"


@pytest.mark.parametrize("report", REPORTS)
def test_foreign_branch_other_company_and_non_member_are_404(as_user, seeded, report) -> None:
    client = as_user("reportes.test")
    assert client.get(branch_url(seeded, report, uuid4()), params=PERIOD).status_code == 404
    other = f"/api/v1/companies/{uuid4()}/branches/{seeded.branches[0].id}/reports/{report}"
    assert client.get(other, params=PERIOD).status_code == 404
    seeded.members.discard("sub-reportes.test")
    assert client.get(branch_url(seeded, report), params=PERIOD).status_code == 404
    owners = {"sales_by_product", "sales_by_branch", "purchase_period"}
    assert not owners & set(seeded.log.names())


def test_inactive_branch_by_uuid(as_user, seeded) -> None:
    closed = seeded.branches[2].id
    assert as_user("reportes.test").get(branch_url(seeded, "purchases", closed), params=PERIOD).status_code == 200


@pytest.mark.parametrize("report", REPORTS)
def test_permission_matrix(as_user, seeded, report) -> None:
    for name in USERS:
        response = as_user(name).get(branch_url(seeded, report), params=PERIOD)
        assert response.status_code == (200 if name in CAN[report] else 403), (name, report)
        if response.status_code == 403:
            assert "perm:" not in response.text


@pytest.mark.parametrize("report", REPORTS)
def test_csv_of_branch_routes(as_user, seeded, report) -> None:
    client = as_user("admin.test")
    response = client.get(branch_url(seeded, report), params={**PERIOD, "format": "csv"})
    assert response.status_code == 200 and response.text.startswith("﻿")
    assert f'{report}-{seeded.branches[0].id}-' in response.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(response.text[1:])))
    assert rows[-1][0] == "TOTAL FILAS"
    data = client.get(branch_url(seeded, report), params=PERIOD).json()
    assert int(rows[-1][1]) == data.get("total_records", len(data["items"]))
