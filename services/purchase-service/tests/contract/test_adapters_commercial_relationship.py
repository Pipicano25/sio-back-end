"""Adaptador de Commercial Relationship (contratos 007 y 010; T015)."""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from purchase_service.application.exceptions import DependencyUnavailableError
from purchase_service.infrastructure.commercial_relationship_directory import HTTPCommercialDirectory
from tests.contract.adapter_support import Recorder, Tokens, json_response, timeout

BASE = "http://commercial-relationship.test/api/v1"


def adapter(handler) -> tuple[HTTPCommercialDirectory, Recorder]:
    recorder = Recorder(handler)
    return HTTPCommercialDirectory(base_url=BASE, timeout_seconds=1, tokens=Tokens(), transport=recorder.transport), recorder


def test_supplier_condition_and_supplier_product() -> None:
    company, supplier, org, condition, kind, product, sp = (uuid4() for _ in range(7))

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/company-suppliers/" in path:
            return httpx.Response(200, json={"company_id": str(company), "organization_identity_id": str(org), "display_name": "Prov", "status": "BLOCKED"})
        if "/supplier-payment-conditions/" in path:
            return httpx.Response(200, json={
                "company_id": str(company), "company_supplier_id": str(supplier), "payment_condition_type_id": str(kind),
                "currency_code": "COP", "payment_terms_days": 30, "valid_from": "2026-01-01", "valid_to": None, "status": "ACTIVE",
            })
        return httpx.Response(200, json={
            "company_id": str(company), "company_supplier_id": str(supplier), "company_product_id": str(product),
            "company_product_presentation_id": None, "expected_supplier_lead_time_hours": "48.50", "status": "ACTIVE",
        })

    cr, recorder = adapter(handler)
    assert cr.get_supplier(supplier).status == "BLOCKED"
    info = cr.get_payment_condition(condition)
    assert info.payment_terms_days == 30 and info.valid_from.isoformat() == "2026-01-01" and info.valid_to is None
    assert cr.get_supplier_product(sp).expected_supplier_lead_time_hours == Decimal("48.50")
    assert [request.url.path for request in recorder.requests] == [
        f"/api/v1/company-suppliers/{supplier}",
        f"/api/v1/supplier-payment-conditions/{condition}",
        f"/api/v1/supplier-products/{sp}",
    ]


def test_batch_lookups_send_distinct_ids_and_skip_not_found() -> None:
    company, found, missing, global_product = uuid4(), uuid4(), uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        ids = json.loads(request.content)["ids"]
        assert len(ids) == len(set(ids))
        return httpx.Response(200, json={"items": [
            {"id": str(found), "found": True, "company_id": str(company), "global_product_id": str(global_product),
             "internal_code": "001", "display_name": "P", "is_purchasable": True, "inventory_control_enabled": False, "status": "ACTIVE"},
            {"id": str(missing), "found": False},
        ]})

    cr, recorder = adapter(handler)
    result = cr.lookup_products([found, missing, found])
    assert set(result) == {found} and result[found].inventory_control_enabled is False
    assert recorder.requests[0].url.path == "/api/v1/company-products/batch-lookup"


def test_presentations_batch() -> None:
    company, presentation, product, global_presentation = uuid4(), uuid4(), uuid4(), uuid4()
    cr, recorder = adapter(json_response(200, {"items": [{
        "id": str(presentation), "found": True, "company_id": str(company), "company_product_id": str(product),
        "global_product_presentation_id": str(global_presentation), "is_purchasable": True, "status": "ACTIVE",
    }]}))
    assert cr.lookup_presentations([presentation])[presentation].global_product_presentation_id == global_presentation
    assert recorder.requests[0].url.path == "/api/v1/company-product-presentations/batch-lookup"


def test_404_is_none() -> None:
    cr, _ = adapter(json_response(404))
    assert cr.get_supplier(uuid4()) is None
    assert cr.get_payment_condition(uuid4()) is None
    assert cr.get_supplier_product(uuid4()) is None


@pytest.mark.parametrize("handler", [json_response(503), json_response(403), timeout, json_response(200, {"items": "x"})])
def test_unavailable(handler) -> None:
    cr, _ = adapter(handler)
    with pytest.raises(DependencyUnavailableError) as error:
        cr.lookup_products([uuid4()])
    assert error.value.provider == "commercial-relationship"


# ------------------------------------------------- cobertura de políticas (spec 021, FR-021-35; contrato CR §3b)


def _coverage_handler(covered: set, *, omit=None, extra=None):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        items = [
            {"company_product_presentation_id": value, "found": True, "covered": value in covered, "price_list_ids": []}
            for value in body["company_product_presentation_ids"] if value != omit
        ]
        if extra:
            items.append({"company_product_presentation_id": extra, "found": True, "covered": True, "price_list_ids": []})
        return httpx.Response(200, json={"items": items})

    return handler


def test_coverage_sends_the_company_currency_and_batches_of_100() -> None:
    company = uuid4()
    ids = [uuid4() for _ in range(150)]
    covered = {str(value) for value in ids[::2]}
    directory, recorder = adapter(_coverage_handler(covered))
    result = directory.lookup_pricing_coverage(company, "COP", [*ids, ids[0]])  # repetidos una sola vez
    assert result == {value: str(value) in covered for value in ids}
    assert [request.url.path for request in recorder.requests] == [f"/api/v1/companies/{company}/pricing-policies/coverage"] * 2
    sent = [json.loads(request.content) for request in recorder.requests]
    assert [len(body["company_product_presentation_ids"]) for body in sent] == [100, 50]
    assert {body["currency_code"] for body in sent} == {"COP"}
    assert all(request.headers["Authorization"].startswith("Bearer tecnico-") for request in recorder.requests)


def test_coverage_ignores_unrequested_items_and_requires_every_answer() -> None:
    wanted, intruder = uuid4(), uuid4()
    directory, _ = adapter(_coverage_handler({str(wanted)}, extra=str(intruder)))
    assert directory.lookup_pricing_coverage(uuid4(), "COP", [wanted]) == {wanted: True}
    directory, _ = adapter(_coverage_handler(set(), omit=str(wanted)))
    with pytest.raises(DependencyUnavailableError):  # sin respuesta para una pedida: nunca se asume cobertura
        directory.lookup_pricing_coverage(uuid4(), "COP", [wanted])


def test_coverage_not_found_is_not_covered() -> None:
    value = uuid4()
    handler = json_response(200, {"items": [{"company_product_presentation_id": str(value), "found": False,
                                             "covered": False, "price_list_ids": []}]})
    directory, _ = adapter(handler)
    assert directory.lookup_pricing_coverage(uuid4(), "COP", [value]) == {value: False}


@pytest.mark.parametrize("handler", [json_response(500), json_response(403), json_response(404), json_response(422), timeout,
                                     json_response(200, {"items": "x"}),
                                     json_response(200, {"items": [{"company_product_presentation_id": "no-uuid"}]})])
def test_coverage_technical_errors_are_unavailable(handler) -> None:
    directory, _ = adapter(handler)
    with pytest.raises(DependencyUnavailableError) as error:
        directory.lookup_pricing_coverage(uuid4(), "COP", [uuid4()])
    assert error.value.provider == "commercial-relationship"
