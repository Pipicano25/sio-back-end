"""Adaptadores HTTP frente a los contratos de los propietarios (`contracts/owner-extensions.md`), con
`httpx.MockTransport`: rutas, parámetros, **propagación del token del usuario** (DR-07), lectura de los cuerpos y
traducción de estados (`401`, `403`, `404`, `5xx`, cuerpo inválido)."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime
from uuid import uuid4

import httpx
import pytest

from business_reporting_service.application.exceptions import (
    DependencyUnavailableError,
    NotFoundError,
    OwnerForbiddenError,
    UnauthenticatedError,
)
from business_reporting_service.infrastructure.catalog import HTTPCommercialRelationship, HTTPProductCatalog
from business_reporting_service.infrastructure.http_client import AsyncDependencyClient, UserCaller
from business_reporting_service.infrastructure.inventory import HTTPInventory
from business_reporting_service.infrastructure.operational_context import HTTPOperationalContext
from business_reporting_service.infrastructure.purchase import HTTPPurchase
from business_reporting_service.infrastructure.sales import HTTPSales

AUTH = "Bearer token-del-usuario"
COMPANY = uuid4()
BRANCH = uuid4()


def caller(handler, provider="sales"):
    seen = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = AsyncDependencyClient(provider=provider, base_url="http://owner.test/api/v1", timeout_seconds=1,
                                   transport=httpx.MockTransport(wrapped))
    return UserCaller(client, AUTH), seen


def run(coroutine):
    return asyncio.run(coroutine)


def test_sales_by_product_sends_user_token_and_parses() -> None:
    product = uuid4()
    body = {"items": [{"company_product_id": str(product), "product_code": "A-1", "product_name": "A",
                       "currency_code": "COP", "quantity_base": "12.0000", "amount": "1500.00", "sales_count": 2,
                       "presentations": None}],
            "totals": [{"currency_code": "COP", "amount": "1500.00", "sales_count": 2}]}
    user, seen = caller(lambda r: httpx.Response(200, json=body))
    result = run(HTTPSales(user).by_product(COMPANY, date_from=date(2026, 10, 1), date_to=date(2026, 10, 18),
                                            branch_ids=[BRANCH], order_by="quantity_base", limit=20,
                                            include_presentations=False))
    [request] = seen
    assert request.headers["authorization"] == AUTH
    assert request.url.path == f"/api/v1/companies/{COMPANY}/sales-aggregates/by-product"
    assert request.url.params.get_list("branch_id") == [str(BRANCH)]
    assert request.url.params["order_by"] == "quantity_base" and request.url.params["include_presentations"] == "false"
    assert result.items[0].quantity_base == 12 and result.totals[0].sales_count == 2


@pytest.mark.parametrize(("status", "error"), [(401, UnauthenticatedError), (403, OwnerForbiddenError),
                                               (404, NotFoundError), (500, DependencyUnavailableError),
                                               (422, DependencyUnavailableError)])
def test_owner_statuses_are_translated(status, error) -> None:
    user, _ = caller(lambda r: httpx.Response(status, json={}))
    with pytest.raises(error):
        run(HTTPSales(user).by_branch(COMPANY, date_from=date(2026, 10, 1), date_to=date(2026, 10, 2), branch_ids=[]))


def test_invalid_body_is_503() -> None:
    user, _ = caller(lambda r: httpx.Response(200, json={"items": [{"branch_id": "no-uuid"}]}))
    with pytest.raises(DependencyUnavailableError):
        run(HTTPSales(user).by_branch(COMPANY, date_from=date(2026, 10, 1), date_to=date(2026, 10, 2), branch_ids=[]))


def test_network_error_is_503() -> None:
    def boom(request):
        raise httpx.ConnectError("caído")

    user, _ = caller(boom)
    with pytest.raises(DependencyUnavailableError):
        run(HTTPSales(user).by_branch(COMPANY, date_from=date(2026, 10, 1), date_to=date(2026, 10, 2), branch_ids=[]))


def test_purchase_period_parameters_and_body() -> None:
    row = {"id": str(uuid4()), "operation_date": "2026-10-05", "received_at": None, "branch_id": str(BRANCH),
           "supplier_name": "P", "supplier_identification": "900", "number": "OC-1", "supplier_document_number": None,
           "status": "CONFIRMED", "category": "PENDING_RECEIPT", "receipt_status": "PENDING", "currency_code": "COP",
           "total": "10.00"}
    totals = {"currency_code": "COP", "received_count": 0, "received_total": "0.00", "pending_receipt_count": 1,
              "pending_receipt_total": "10.00", "cancelled_count": 0, "cancelled_total": "0.00",
              "effective_total": "10.00"}
    user, seen = caller(lambda r: httpx.Response(200, json={"items": [row], "totals": [totals], "total_records": 1,
                                                             "page": 1, "page_size": 100, "total_pages": 1}), "purchase")
    page = run(HTTPPurchase(user).period(COMPANY, date_from=date(2026, 10, 1), date_to=date(2026, 10, 18),
                                         branch_ids=[], categories=["PENDING_RECEIPT"], page=2, page_size=100))
    params = seen[0].url.params
    assert seen[0].url.path.endswith("/purchase-reports/period") and params["page"] == "2"
    assert params.get_list("category") == ["PENDING_RECEIPT"] and seen[0].headers["authorization"] == AUTH
    assert page.items[0].category == "PENDING_RECEIPT" and page.totals[0].effective_total == 10


def test_inventory_stock_evolution_checks_company_and_branch() -> None:
    item = {"company_product_id": str(uuid4()), "opening_quantity": "1.0000", "entries": "0.0000", "outputs": "0.0000",
            "entry_reversals": "0.0000", "output_reversals": "0.0000", "positive_adjustments": "0.0000",
            "negative_adjustments": "0.0000", "closing_quantity": "1.0000", "movement_count": 0}
    good = {"company_id": str(COMPANY), "branch_id": str(BRANCH), "items": [item], "total_records": 1}
    user, seen = caller(lambda r: httpx.Response(200, json=good), "inventory")
    start = datetime(2026, 10, 1, 5, tzinfo=UTC)
    page = run(HTTPInventory(user).stock_evolution(COMPANY, BRANCH, from_at=start, to_at=start.replace(day=2),
                                                   product_ids=[], page=1, page_size=100))
    assert seen[0].url.path == f"/api/v1/companies/{COMPANY}/branches/{BRANCH}/stock-evolution"
    assert seen[0].url.params["from"] == start.isoformat() and page.items[0].balances()
    other = {**good, "branch_id": str(uuid4())}
    user, _ = caller(lambda r: httpx.Response(200, json=other), "inventory")
    with pytest.raises(DependencyUnavailableError):
        run(HTTPInventory(user).stock_evolution(COMPANY, BRANCH, from_at=start, to_at=start.replace(day=2),
                                                product_ids=[], page=1, page_size=100))


def test_catalog_batches_and_drops_foreign_products() -> None:
    mine, foreign, global_id = uuid4(), uuid4(), uuid4()

    def cr(request):
        payload = json.loads(request.content)
        assert payload["status"] == "ALL" and payload["limit"] == 100 and len(payload["company_product_ids"]) <= 100
        return httpx.Response(200, json={"items": [
            {"id": str(mine), "company_id": str(COMPANY), "global_product_id": str(global_id), "internal_code": "A",
             "display_name": "A"},
            {"id": str(foreign), "company_id": str(uuid4()), "global_product_id": str(uuid4()), "internal_code": "B",
             "display_name": "B"}], "has_more": False})

    user, seen = caller(cr, "commercial-relationship")
    found = run(HTTPCommercialRelationship(user).products(COMPANY, [uuid4() for _ in range(150)]))
    assert len(seen) == 2 and set(found) == {mine}  # 150 ids → 2 lotes; el producto ajeno se descarta
    pc_body = {"items": [{"id": str(global_id), "found": True, "base_unit": {"id": str(uuid4()), "code": "TAB",
                                                                               "name": "Tableta"}}]}
    user, seen = caller(lambda r: httpx.Response(200, json=pc_body), "product-catalog")
    units = run(HTTPProductCatalog(user).base_units([global_id, global_id]))
    assert units[global_id].code == "TAB" and json.loads(seen[0].content) == {"ids": [str(global_id)]}


def test_operational_context_access_and_branches() -> None:
    def oc(request):
        if request.url.path.endswith("/operational-access"):
            return httpx.Response(200, json={"allowed": True, "company_id": str(COMPANY)})
        if request.url.path.endswith(f"/companies/{COMPANY}"):
            return httpx.Response(200, json={"id": str(COMPANY), "timezone": "America/Bogota", "default_currency": "COP"})
        return httpx.Response(200, json={"items": [
            {"id": str(BRANCH), "company_id": str(COMPANY), "code": "PPAL", "name": "Principal", "status": "ACTIVE",
             "effective_timezone": "America/Bogota"},
            {"id": str(uuid4()), "company_id": str(uuid4()), "code": "X", "name": "Ajena", "status": "ACTIVE",
             "effective_timezone": "America/Bogota"}], "total_pages": 1})

    client = AsyncDependencyClient(provider="operational-context", base_url="http://oc.test/api/v1", timeout_seconds=1,
                                   transport=httpx.MockTransport(oc))
    adapter = HTTPOperationalContext(client, AUTH)
    assert run(adapter.has_company_access(COMPANY)) is True
    assert run(adapter.company(COMPANY)).default_currency == "COP"
    assert [b.code for b in run(adapter.branches(COMPANY, status="ACTIVE"))] == ["PPAL"]  # la ajena se descarta
