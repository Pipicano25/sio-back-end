"""Permisos, aislamiento y validación de los reportes (spec 023, FR-023-10 a FR-023-14, FR-023-50).

La matriz usa los roles de la **plantilla del realm**; los dobles de Sales, Purchase, Inventory, CR y PC evalúan el
permiso del propietario sobre el mismo token del usuario (DR-07).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.support import PERIOD, base, branch_base, seed_evolution, seed_purchases, seed_sales
from tests.conftest import USER_ROLES

REPORTS = ("top-selling-products", "sales-by-branch", "purchases", "stock-evolution")
MATRIX = {
    "admin.test": (200, 200, 200, 200),
    "supervisor.test": (200, 200, 200, 200),
    "ventas.test": (200, 403, 403, 403),
    "compras.test": (403, 403, 200, 403),
    "inventario.test": (403, 403, 403, 200),
    "reportes.test": (200, 200, 200, 200),
    "consulta.test": (403, 403, 403, 403),
}


def url(fakes, report: str) -> str:
    return f"{branch_base(fakes)}/{report}" if report == "stock-evolution" else f"{base(fakes)}/{report}"


@pytest.fixture
def seeded(fakes):
    seed_sales(fakes)
    seed_purchases(fakes)
    seed_evolution(fakes)
    return fakes


@pytest.mark.parametrize("username", list(MATRIX))
def test_matrix_per_group_with_template_roles(as_user, seeded, username) -> None:
    for report, expected in zip(REPORTS, MATRIX[username], strict=True):
        for fmt in ("json", "csv"):
            response = as_user(username).get(url(seeded, report), params={**PERIOD, "format": fmt})
            assert response.status_code == expected, (username, report, fmt, response.text[:200])
            if expected == 403:
                assert "perm:" not in response.text


def test_reportes_reads_stock_evolution_without_kardex_permission() -> None:
    roles = USER_ROLES["reportes.test"]
    assert "perm:inventory:stock_evolution:read" in roles
    assert "perm:inventory:movements:read" not in roles and "perm:inventory:valuation:read" not in roles


def test_owner_permission_is_required_too(as_user, as_token, make_token, seeded) -> None:
    """Con el permiso del reporte pero sin el del propietario: `403` genérico (DR-07)."""
    only_report = as_token(make_token("perm:business-reporting:all:read", "perm:operational-context:all:read",
                                      sub="sub-reportes.test"))
    for report in REPORTS:
        response = only_report.get(url(seeded, report), params=PERIOD)
        assert response.status_code == 403, (report, response.text)
        assert "perm:" not in response.text


def test_kardex_permission_alone_does_not_open_stock_evolution(as_token, make_token, seeded) -> None:
    token = as_token(make_token("perm:business-reporting:stock_evolution:read", "perm:inventory:movements:read",
                                "perm:commercial-relationship:company_products:read",
                                "perm:product-catalog:products:read", sub="sub-inventario.test"))
    assert token.get(url(seeded, "stock-evolution"), params=PERIOD).status_code == 403


def test_anonymous_is_401(as_token, seeded) -> None:
    for report in REPORTS:
        response = as_token(None).get(url(seeded, report), params=PERIOD)
        assert response.status_code == 401 and response.json()["code"] == "BUSINESS_REPORTING.UNAUTHENTICATED"


def test_non_member_other_company_and_foreign_branch_are_404_before_owners(as_user, seeded) -> None:
    seeded.members.discard("sub-reportes.test")
    for report in REPORTS:
        assert as_user("reportes.test").get(url(seeded, report), params=PERIOD).status_code == 404
    seeded.members.add("sub-reportes.test")
    other = f"/api/v1/companies/{uuid4()}/reports/top-selling-products"
    assert as_user("reportes.test").get(other, params=PERIOD).status_code == 404
    foreign = f"/api/v1/companies/{seeded.company.id}/branches/{uuid4()}/reports/stock-evolution"
    assert as_user("reportes.test").get(foreign, params=PERIOD).status_code == 404
    assert as_user("reportes.test").get(f"{base(seeded)}/purchases",
                                        params={**PERIOD, "branch_id": str(uuid4())}).status_code == 404
    owners = {"sales_by_product", "sales_by_branch", "purchase_period", "stock_evolution", "company_products_search"}
    assert not owners & set(seeded.log.names())


def test_inactive_branch_can_be_named_explicitly(as_user, seeded) -> None:
    closed = seeded.branches[2]
    response = as_user("reportes.test").get(f"{base(seeded)}/sales-by-branch",
                                            params={**PERIOD, "branch_id": str(closed.id)})
    assert response.status_code == 200
    assert [row["branch_code"] for row in response.json()["items"]] == ["CERRADA"]


@pytest.mark.parametrize("params", [
    {"date_from": "2026-10-10", "date_to": "2026-10-01"},
    {"date_from": "2025-10-01", "date_to": "2026-10-02"},  # 367 días
    {"date_from": "2026-10-01", "date_to": "2026-10-19"},  # mañana en Bogotá (NOW = 2026-10-18)
    {"date_from": "2026-10-01"},
    {**PERIOD, "limit": "101"},
    {**PERIOD, "rank_by": "otro"},
    {**PERIOD, "format": "xlsx"},
    {**PERIOD, "desconocido": "x"},
])
def test_invalid_parameters_are_422(as_user, seeded, params) -> None:
    response = as_user("reportes.test").get(f"{base(seeded)}/top-selling-products", params=params)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "BUSINESS_REPORTING.VALIDATION_ERROR"


def test_branch_or_scope_in_query_of_stock_evolution_is_422(as_user, seeded) -> None:
    for extra in ({"branch_id": str(seeded.branches[1].id)}, {"scope": "COMPANY"}):
        assert as_user("inventario.test").get(url(seeded, "stock-evolution"),
                                              params={**PERIOD, **extra}).status_code == 422


def test_dependency_failure_is_503_without_naming_it(as_user, seeded) -> None:
    seeded.fail.add("sales_by_product")
    response = as_user("reportes.test").get(f"{base(seeded)}/top-selling-products", params=PERIOD)
    assert response.status_code == 503
    assert "sales" not in response.json()["detail"].lower()
