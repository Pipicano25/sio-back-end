"""Adaptador de Commercial Relationship (contratos 007 y 010; P-03; T017)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from sales_service.application.exceptions import DependencyUnavailableError
from sales_service.application.ports import PriceRequestLine
from sales_service.infrastructure.commercial_relationship_directory import HTTPCommercialDirectory
from tests.contract.adapter_support import Recorder, Tokens, expired_then, json_response, timeout

BASE = "http://commercial-relationship.test/api/v1"


def adapter(handler) -> tuple[HTTPCommercialDirectory, Recorder]:
    recorder = Recorder(handler)
    return HTTPCommercialDirectory(base_url=BASE, timeout_seconds=1, tokens=Tokens(), transport=recorder.transport), recorder


def test_customer_person_and_organization() -> None:
    company, person, organization, customer = uuid4(), uuid4(), uuid4(), uuid4()
    bodies = iter(
        [
            {"company_id": str(company), "customer_kind": "PERSON", "person_identity_id": str(person),
             "organization_identity_id": None, "display_name": "Ana", "status": "ACTIVE"},
            {"company_id": str(company), "customer_kind": "ORGANIZATION", "person_identity_id": None,
             "organization_identity_id": str(organization), "display_name": "Tiendas", "status": "INACTIVE"},
        ]
    )
    cr, recorder = adapter(lambda request: httpx.Response(200, json=next(bodies)))
    first = cr.get_customer(customer)
    assert (first.customer_kind, first.person_identity_id, first.organization_identity_id) == ("PERSON", person, None)
    second = cr.get_customer(customer)
    assert (second.organization_identity_id, second.status) == (organization, "INACTIVE")
    assert recorder.requests[0].url.path == f"/api/v1/company-customers/{customer}"
    assert recorder.requests[0].headers["Authorization"] == "Bearer tecnico-1"


def test_batch_lookups_read_is_sellable() -> None:
    company, found, missing, global_product, presentation = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        ids = json.loads(request.content)["ids"]
        assert len(ids) == len(set(ids))
        if request.url.path.endswith("/company-products/batch-lookup"):
            return httpx.Response(200, json={"items": [
                {"id": str(found), "found": True, "company_id": str(company), "global_product_id": str(global_product),
                 "internal_code": "001", "display_name": "P", "is_sellable": False, "inventory_control_enabled": True,
                 "status": "ACTIVE"},
                {"id": str(missing), "found": False},
            ]})
        return httpx.Response(200, json={"items": [{
            "id": str(presentation), "found": True, "company_id": str(company), "company_product_id": str(found),
            "global_product_presentation_id": str(uuid4()), "is_sellable": True, "status": "ACTIVE",
        }]})

    cr, recorder = adapter(handler)
    result = cr.lookup_products([found, missing, found])
    assert set(result) == {found} and result[found].is_sellable is False
    assert cr.lookup_presentations([presentation])[presentation].is_sellable is True
    assert [request.url.path for request in recorder.requests] == [
        "/api/v1/company-products/batch-lookup",
        "/api/v1/company-product-presentations/batch-lookup",
    ]


def test_resolve_prices_sends_the_requested_list_only() -> None:
    company, product, presentation, price_list, item = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
    at = datetime(2026, 10, 7, 15, 0, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["at"] == at.isoformat()
        assert body["lines"] == [
            {"line_id": "0", "company_product_id": str(product), "company_product_presentation_id": str(presentation),
             "price_list_id": str(price_list)},
            {"line_id": "1", "company_product_id": str(product)},
        ]
        return httpx.Response(200, json={"at": body["at"], "items": [
            {"line_id": "0", "found": True, "resolution": "PRICE_LIST_ITEM", "basis": "PRESENTATION",
             "unit_price": "16000.00", "currency_code": "COP", "price_list_id": str(price_list),
             "price_list_item_id": str(item), "company_product_status": "ACTIVE", "presentation_status": "ACTIVE"},
            {"line_id": "1", "found": True, "resolution": "COMPANY_PRODUCT_SALE_PRICE", "basis": "BASE_UNIT",
             "unit_price": None, "currency_code": "COP", "price_list_id": None, "price_list_item_id": None,
             "company_product_status": "ACTIVE", "presentation_status": None},
        ]})

    cr, recorder = adapter(handler)
    prices = cr.resolve_prices(
        company,
        [PriceRequestLine("0", product, presentation, price_list), PriceRequestLine("1", product, None, None)],
        at,
    )
    assert recorder.requests[0].url.path == f"/api/v1/companies/{company}/applicable-prices/resolve"
    assert prices["0"].unit_price == Decimal("16000.00") and prices["0"].price_list_item_id == item
    assert prices["1"].resolution == "COMPANY_PRODUCT_SALE_PRICE" and prices["1"].unit_price is None


def test_get_price_list_for_p03() -> None:
    company, price_list = uuid4(), uuid4()
    cr, recorder = adapter(json_response(200, {"company_id": str(company), "status": "INACTIVE", "code": "X"}))
    info = cr.get_price_list(price_list)
    assert (info.company_id, info.status) == (company, "INACTIVE")
    assert recorder.requests[0].url.path == f"/api/v1/price-lists/{price_list}"
    missing, _ = adapter(json_response(404))
    assert missing.get_price_list(price_list) is None


def test_404_is_none_and_token_renewed_once() -> None:
    cr, _ = adapter(json_response(404))
    assert cr.get_customer(uuid4()) is None
    renewed, recorder = adapter(expired_then({"company_id": str(uuid4()), "customer_kind": "PERSON",
                                              "person_identity_id": str(uuid4()), "display_name": "A", "status": "ACTIVE"}))
    assert renewed.get_customer(uuid4()).customer_kind == "PERSON"
    assert len(recorder.requests) == 2


@pytest.mark.parametrize(
    "handler",
    [json_response(503), json_response(403), json_response(422), timeout, json_response(200, {"items": "x"})],
)
def test_unavailable(handler) -> None:
    cr, _ = adapter(handler)
    with pytest.raises(DependencyUnavailableError) as error:
        cr.resolve_prices(uuid4(), [PriceRequestLine("0", uuid4(), None, None)], datetime.now(UTC))
    assert error.value.provider == "commercial-relationship"
