"""Adaptador de lecturas por lotes de Product Catalog (spec 027, T006) con `httpx.MockTransport`.

Rutas y formatos tomados de `services/product-catalog-service` (`api/presentations.py`, `api/products.py` y
`api/product_summaries.py`).
"""

from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest

from commercial_relationship_service.application.exceptions import (
    PRODUCT_CATALOG_ACCESS_DENIED,
    DependencyUnavailableError,
)
from commercial_relationship_service.infrastructure.product_catalog_bulk_directory import (
    HTTPProductCatalogBulkDirectory,
)
from tests.contract.test_product_catalog_adapter import FakeTokens


def _directory(handler, tokens=None) -> HTTPProductCatalogBulkDirectory:
    return HTTPProductCatalogBulkDirectory(
        base_url="http://pc.test/api/v1",
        timeout_seconds=1.0,
        token_client=tokens or FakeTokens(),
        transport=httpx.MockTransport(handler),
    )


def test_lookup_presentations_keeps_request_order_and_missing_ones():
    found, missing, product = uuid4(), uuid4(), uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(path=request.url.path, body=json.loads(request.content), auth=request.headers["authorization"])
        return httpx.Response(
            200,
            json={
                "items": [
                    {"id": str(missing), "found": False},
                    {
                        "id": str(found),
                        "found": True,
                        "global_product_id": str(product),
                        "status": "ACTIVE",
                        "eligible_for_adoption": True,
                        "code": "UND",
                    },
                ]
            },
        )

    result = _directory(handler).lookup_presentations([found, missing])

    assert seen == {
        "path": "/api/v1/presentations/batch-lookup",
        "body": {"ids": [str(found), str(missing)]},
        "auth": "Bearer tech-1",
    }
    assert [(item.id, item.ref.found) for item in result] == [(found, True), (missing, False)]
    assert result[0].ref.global_product_id == product and result[0].ref.eligible_for_adoption is True


def test_lookup_products_reads_status_and_eligibility():
    product = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/products/batch-lookup"
        return httpx.Response(
            200,
            json={"items": [{"id": str(product), "found": True, "status": "INACTIVE", "eligible_for_adoption": False}]},
        )

    (item,) = _directory(handler).lookup_products([product])
    assert (item.ref.found, item.ref.status, item.ref.eligible_for_adoption) == (True, "INACTIVE", False)


def test_product_summaries_reads_name_and_identifiers():
    product, presentation, missing = uuid4(), uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/products/summaries/batch-lookup"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": str(product),
                        "found": True,
                        "canonical_name": "Acetaminofén 500 mg",
                        "status": "ACTIVE",
                        "identifiers": [
                            {
                                "type": "GTIN",
                                "value": "7702001234567",
                                "is_primary": True,
                                "global_product_presentation_id": str(presentation),
                            },
                            {"type": "OTHER", "value": "X", "is_primary": False, "global_product_presentation_id": None},
                        ],
                    },
                    {"id": str(missing), "found": False},
                ]
            },
        )

    summaries = _directory(handler).product_summaries([product, missing])

    assert summaries[product].canonical_name == "Acetaminofén 500 mg"
    assert summaries[product].identifiers[0].global_product_presentation_id == presentation
    assert summaries[product].identifiers[1].global_product_presentation_id is None
    assert summaries[missing].found is False


def test_product_presentations_asks_only_active_and_reads_base():
    product, base = uuid4(), uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(method=request.method, path=request.url.path, query=dict(request.url.params))
        return httpx.Response(
            200,
            json=[
                {
                    "id": str(base),
                    "global_product_id": str(product),
                    "status": "ACTIVE",
                    "is_base": True,
                    "eligible_for_adoption": True,
                }
            ],
        )

    (item,) = _directory(handler).product_presentations(product)

    assert seen == {"method": "GET", "path": f"/api/v1/products/{product}/presentations", "query": {"status": "ACTIVE"}}
    assert (item.id, item.is_base) == (base, True)


def test_product_presentations_of_missing_product_is_empty():
    assert _directory(lambda request: httpx.Response(404, json={})).product_presentations(uuid4()) == []


def test_match_products_sends_filter_and_returns_last_position():
    category, first, last = uuid4(), uuid4(), uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(path=request.url.path, body=json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "items": [
                    {"id": str(first), "position": {"k": ["a"], "id": str(first)}},
                    {"id": str(last), "position": {"k": ["b"], "id": str(last)}},
                ],
                "has_more": True,
            },
        )

    page = _directory(handler).match_products(
        category_ids=[category], brand_ids=[], include_descendants=True, after=None, limit=2
    )

    assert seen["path"] == "/api/v1/products/match"
    assert seen["body"] == {
        "category_ids": [str(category)],
        "brand_ids": [],
        "include_descendants": True,
        "status": "ACTIVE",
        "after": None,
        "limit": 2,
    }
    assert page.ids == [first, last] and page.after == {"k": ["b"], "id": str(last)} and page.has_more is True


@pytest.mark.parametrize(
    "response",
    [httpx.Response(500, json={}), httpx.Response(200, json={"unexpected": True}), httpx.Response(200, text="x")],
)
def test_unexpected_answers_are_dependency_unavailable(response):
    with pytest.raises(DependencyUnavailableError):
        _directory(lambda request: response).lookup_presentations([uuid4()])


def test_renews_token_once_and_reports_access_denied():
    tokens = FakeTokens()

    with pytest.raises(DependencyUnavailableError) as error:
        _directory(lambda request: httpx.Response(401), tokens).lookup_products([uuid4()])

    assert tokens.invalidated == 1 and tokens.issued == 2
    assert error.value.cause == PRODUCT_CATALOG_ACCESS_DENIED
