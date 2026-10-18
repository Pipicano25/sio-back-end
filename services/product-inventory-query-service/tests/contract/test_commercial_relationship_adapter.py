"""Adaptador de Commercial Relationship (T063; FR-022-12, CP-69, CP-70)."""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

import httpx
import pytest

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.ports import PriceLine, ProductCriteria
from product_inventory_query_service.infrastructure.commercial_relationship import HTTPCommercialRelationship
from product_inventory_query_service.observability import SERVICE_LOGGER
from tests.contract.adapter_support import Recorder, technical


def _cr(responder) -> tuple[HTTPCommercialRelationship, Recorder]:
    recorder = Recorder(responder)
    return HTTPCommercialRelationship(technical("commercial-relationship", recorder)), recorder


def _product(company, name="Crema", **extra):
    product_id = uuid4()
    return {
        "id": str(product_id), "company_id": str(company), "global_product_id": str(uuid4()), "internal_code": "C1",
        "reference_code": None, "display_name": name, "status": "ACTIVE", "is_sellable": True, "is_purchasable": True,
        "inventory_control_enabled": True, "created_at": "2026-10-01T10:00:00Z", "version": 1,
        "position": {"k": [name], "id": str(product_id)}, **extra,
    }


def test_search_conductor_sends_criteria_and_keeps_position_untouched() -> None:
    company = uuid4()
    row = _product(company)
    cr, recorder = _cr(lambda r: httpx.Response(200, json={"items": [row], "has_more": True}))
    after = {"k": ["Alfa"], "id": str(uuid4())}

    products, has_more = asyncio.run(cr.search_products(
        company, ProductCriteria(search="col", inventory_control_enabled=True), sort_key="display_name",
        descending=False, limit=40, after=after))

    assert has_more is True and products[0].position == row["position"]
    request = recorder.requests[0]
    assert request.url.path == f"/api/v1/companies/{company}/company-products/search"
    assert request.headers["authorization"] == "Bearer token-tecnico"
    assert recorder.bodies()[0] == {"status": "ACTIVE", "sort": {"key": "display_name", "direction": "asc"},
                                    "limit": 40, "search": "col", "inventory_control_enabled": True, "after": after}


def test_search_evaluator_mode_sends_ids() -> None:
    company, ids = uuid4(), [uuid4(), uuid4()]
    cr, recorder = _cr(lambda r: httpx.Response(200, json={"items": [], "has_more": False}))
    asyncio.run(cr.search_products(company, ProductCriteria(), sort_key="display_name", descending=True, limit=2,
                                   global_product_ids=ids))
    body = recorder.bodies()[0]
    assert body["global_product_ids"] == [str(i) for i in ids] and body["sort"]["direction"] == "desc"


def test_rows_of_another_company_are_discarded_and_logged(caplog) -> None:
    company = uuid4()
    rows = [_product(company, "Propio"), _product(uuid4(), "Ajeno")]
    cr, _ = _cr(lambda r: httpx.Response(200, json={"items": rows, "has_more": False}))
    logger = logging.getLogger(SERVICE_LOGGER)
    logger.propagate = True
    try:
        with caplog.at_level(logging.ERROR, logger=SERVICE_LOGGER):
            products, _ = asyncio.run(cr.search_products(company, ProductCriteria(), sort_key="display_name",
                                                         descending=False, limit=10))
    finally:
        logger.propagate = False
    assert [p.display_name for p in products] == ["Propio"]
    assert "Incidente de integridad" in caplog.text


def test_presentations_by_products_in_batches_of_100() -> None:
    company = uuid4()
    ids = [uuid4() for _ in range(150)]

    def responder(request):
        return httpx.Response(200, json={"items": [{
            "id": str(uuid4()), "company_id": str(company), "company_product_id": request_id,
            "global_product_presentation_id": str(uuid4()), "internal_code": None, "sku": "S", "reference_code": None,
            "is_purchasable": True, "is_sellable": True, "is_default_purchase": False, "is_default_sale": False,
            "status": "ACTIVE", "version": 1}
            for request_id in __import__("json").loads(request.content)["company_product_ids"][:1]]})

    cr, recorder = _cr(responder)
    presentations = asyncio.run(cr.presentations_by_products(company, ids))
    assert [len(body["company_product_ids"]) for body in recorder.bodies()] == [100, 50]
    assert len(presentations) == 2


def test_prices_in_batches_of_100_mapped_by_presentation() -> None:
    company = uuid4()
    lines = [PriceLine(uuid4(), uuid4(), None) for _ in range(120)]

    def responder(request):
        body = __import__("json").loads(request.content)
        return httpx.Response(200, json={"at": "2026-10-17T10:00:00Z", "items": [
            {"line_id": line["line_id"], "found": True, "resolution": "PRICE_LIST_ITEM", "unit_price": "4500.00",
             "currency_code": "COP", "price_list_id": str(uuid4()), "price_list_item_id": str(uuid4())}
            for line in body["lines"]]})

    cr, recorder = _cr(responder)
    prices = asyncio.run(cr.resolve_prices(company, lines))
    assert [len(body["lines"]) for body in recorder.bodies()] == [100, 20]
    assert {p.company_product_presentation_id for p in prices} == {line.company_product_presentation_id for line in lines}


def test_adopted_count_uses_total_records_of_the_listing() -> None:
    company = uuid4()
    cr, recorder = _cr(lambda r: httpx.Response(200, json={"items": [], "page": 1, "page_size": 1,
                                                           "total_records": 2340, "total_pages": 2340}))
    assert asyncio.run(cr.count_adopted(company)) == 2340
    params = recorder.requests[0].url.params
    assert (params["status"], params["inventory_control_enabled"], params["page_size"]) == ("ACTIVE", "true", "1")


@pytest.mark.parametrize("status", [401, 403])
def test_rejected_technical_identity_is_503(status) -> None:
    cr, _ = _cr(lambda r: httpx.Response(status, json={}))
    with pytest.raises(DependencyUnavailableError) as exc:
        asyncio.run(cr.count_adopted(uuid4()))
    assert exc.value.cause == "identidad_tecnica_rechazada"


def test_unexpected_body_is_503() -> None:
    cr, _ = _cr(lambda r: httpx.Response(200, json={"items": [{"id": "x"}], "has_more": False}))
    with pytest.raises(DependencyUnavailableError):
        asyncio.run(cr.search_products(uuid4(), ProductCriteria(), sort_key="display_name", descending=False, limit=5))
