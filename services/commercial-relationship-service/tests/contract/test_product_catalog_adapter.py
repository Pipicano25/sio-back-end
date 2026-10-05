"""Adaptador de Product Catalog con `httpx.MockTransport` (R-04, R-05, RC-05, RC-06).

Contrato: `specs/007-commercial-relationship-core/contracts/product-catalog-dependency.md`.
"""

from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest

from commercial_relationship_service.application.exceptions import (
    PRODUCT_CATALOG_ACCESS_DENIED,
    DependencyUnavailableError,
    GlobalPresentationNotEligibleError,
    GlobalPresentationNotFoundError,
    GlobalPresentationOfOtherProductError,
    GlobalProductNotEligibleError,
    GlobalProductNotFoundError,
)
from commercial_relationship_service.infrastructure.product_catalog_directory import (
    HTTPProductCatalogDirectory,
)
from commercial_relationship_service.observability import reset_trace_id, set_trace_id


class FakeTokens:
    def __init__(self) -> None:
        self.issued = 0
        self.invalidated = 0

    def get_token(self) -> str:
        self.issued += 1
        return f"tech-{self.issued}"

    def invalidate(self) -> None:
        self.invalidated += 1


def _directory(handler, tokens=None) -> HTTPProductCatalogDirectory:
    return HTTPProductCatalogDirectory(
        base_url="http://pc.test/api/v1",
        timeout_seconds=1.0,
        token_client=tokens or FakeTokens(),
        transport=httpx.MockTransport(handler),
    )


def test_lookup_sends_batch_with_technical_token_and_trace():
    product = uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers["authorization"]
        seen["trace"] = request.headers.get("traceparent")
        return httpx.Response(
            200,
            json={"items": [{"id": str(product), "found": True, "status": "ACTIVE", "eligible_for_adoption": True}]},
        )

    token = set_trace_id("0af7651916cd43dd8448eb211c80319c")
    try:
        ref = _directory(handler).lookup_product(product)
    finally:
        reset_trace_id(token)

    assert seen["path"] == "/api/v1/products/batch-lookup"
    assert seen["body"] == {"ids": [str(product)]}
    assert seen["auth"] == "Bearer tech-1"
    assert seen["trace"].startswith("00-0af7651916cd43dd8448eb211c80319c-")
    assert ref.found and ref.status == "ACTIVE" and ref.eligible_for_adoption


def test_lookup_not_found_inactive_and_not_eligible():
    product = uuid4()

    def respond(item):
        return lambda request: httpx.Response(200, json={"items": [item]})

    assert not _directory(respond({"id": str(product), "found": False})).lookup_product(product).found

    ref = _directory(respond({"id": str(product), "found": True, "status": "INACTIVE", "eligible_for_adoption": False})).lookup_product(product)
    assert ref.status == "INACTIVE"

    ref = _directory(respond({"id": str(product), "found": True, "status": "ACTIVE", "eligible_for_adoption": False})).lookup_product(product)
    assert ref.eligible_for_adoption is False


def test_first_use_sends_null_presentation():
    product = uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"global_product_id": str(product)})

    _directory(handler).register_first_use(product)
    assert seen["path"] == f"/api/v1/products/{product}/first-use"
    assert seen["body"] == {"global_product_presentation_id": None}


def test_first_use_error_mapping():
    product = uuid4()

    with pytest.raises(GlobalProductNotFoundError):
        _directory(lambda request: httpx.Response(404)).register_first_use(product)

    with pytest.raises(GlobalProductNotEligibleError):
        _directory(
            lambda request: httpx.Response(422, json={"code": "PRODUCT_CATALOG.NOT_ELIGIBLE_FOR_FIRST_USE"})
        ).register_first_use(product)

    for response in (
        httpx.Response(422, json={"code": "PRODUCT_CATALOG.VALIDATION_ERROR"}),
        httpx.Response(500),
        httpx.Response(409),
    ):
        with pytest.raises(DependencyUnavailableError) as error:
            _directory(lambda request, r=response: r).register_first_use(product)
        assert error.value.provider == "product-catalog"


def test_401_renews_token_and_retries_once():
    tokens = FakeTokens()
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["authorization"])
        if len(seen) == 1:
            return httpx.Response(401)
        return httpx.Response(200, json={"items": []})

    _directory(handler, tokens).lookup_product(uuid4())
    assert seen == ["Bearer tech-1", "Bearer tech-2"]
    assert tokens.invalidated == 1


@pytest.mark.parametrize("statuses", [(401, 401), (403,)])
def test_second_401_or_403_is_unavailable_with_access_denied_cause(statuses):
    responses = iter(statuses)

    with pytest.raises(DependencyUnavailableError) as error:
        _directory(lambda request: httpx.Response(next(responses))).register_first_use(uuid4())

    assert error.value.provider == "product-catalog"
    assert error.value.cause == PRODUCT_CATALOG_ACCESS_DENIED


@pytest.mark.parametrize("exception", [httpx.ConnectError("x"), httpx.ReadTimeout("x")])
def test_network_errors(exception):
    def handler(request):
        raise exception

    with pytest.raises(DependencyUnavailableError):
        _directory(handler).lookup_product(uuid4())


def test_unexpected_lookup_body():
    with pytest.raises(DependencyUnavailableError):
        _directory(lambda request: httpx.Response(200, json={"x": 1})).lookup_product(uuid4())


# --------------------------------------------------------------------------
# Fase B (T007; R-07; contracts/product-catalog-dependency.md de la 010)
# --------------------------------------------------------------------------


def test_lookup_presentation_found_with_owner_product():
    presentation, product = uuid4(), uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(
            200,
            json={"items": [{"id": str(presentation), "found": True, "global_product_id": str(product),
                             "status": "ACTIVE", "eligible_for_adoption": True}]},
        )

    ref = _directory(handler).lookup_presentation(presentation)

    assert seen == {
        "path": "/api/v1/presentations/batch-lookup",
        "body": {"ids": [str(presentation)]},
        "auth": "Bearer tech-1",
    }
    assert ref.found and ref.global_product_id == product
    assert ref.status == "ACTIVE" and ref.eligible_for_adoption


def test_lookup_presentation_not_found_inactive_not_eligible():
    presentation, product = uuid4(), uuid4()

    def respond(item):
        return lambda request: httpx.Response(200, json={"items": [item]})

    assert not _directory(respond({"id": str(presentation), "found": False})).lookup_presentation(presentation).found

    ref = _directory(respond({"id": str(presentation), "found": True, "global_product_id": str(product),
                              "status": "INACTIVE", "eligible_for_adoption": False})).lookup_presentation(presentation)
    assert ref.status == "INACTIVE" and ref.eligible_for_adoption is False


def test_lookup_presentation_unexpected_body_is_unavailable():
    presentation = uuid4()

    for response in (
        httpx.Response(200, json={"x": 1}),
        httpx.Response(200, json={"items": [{"id": str(presentation), "found": True, "global_product_id": "no-uuid"}]}),
        httpx.Response(500),
    ):
        with pytest.raises(DependencyUnavailableError) as error:
            _directory(lambda request, r=response: r).lookup_presentation(presentation)
        assert error.value.provider == "product-catalog"


def test_get_product_base_unit():
    product, unit = uuid4(), uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"], seen["path"] = request.method, request.url.path
        return httpx.Response(200, json={"id": str(product), "base_unit_id": str(unit)})

    assert _directory(handler).get_product_base_unit(product) == unit
    assert seen == {"method": "GET", "path": f"/api/v1/products/{product}"}
    assert _directory(lambda request: httpx.Response(404)).get_product_base_unit(product) is None

    for response in (httpx.Response(200, json={"id": str(product)}), httpx.Response(503)):
        with pytest.raises(DependencyUnavailableError):
            _directory(lambda request, r=response: r).get_product_base_unit(product)


def test_first_use_with_presentation_sends_its_uuid():
    product, presentation = uuid4(), uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={})

    _directory(handler).register_first_use(product, presentation)
    assert seen["body"] == {"global_product_presentation_id": str(presentation)}


def test_first_use_with_presentation_error_mapping():
    product, presentation = uuid4(), uuid4()

    with pytest.raises(GlobalPresentationNotFoundError):
        _directory(lambda request: httpx.Response(404)).register_first_use(product, presentation)

    with pytest.raises(GlobalPresentationNotEligibleError):
        _directory(
            lambda request: httpx.Response(422, json={"code": "PRODUCT_CATALOG.NOT_ELIGIBLE_FOR_FIRST_USE"})
        ).register_first_use(product, presentation)

    with pytest.raises(GlobalPresentationOfOtherProductError):
        _directory(
            lambda request: httpx.Response(422, json={"code": "PRODUCT_CATALOG.PRESENTATION_OF_OTHER_PRODUCT"})
        ).register_first_use(product, presentation)

    for response in (httpx.Response(500), httpx.Response(403), httpx.Response(422, json={"code": "X"})):
        with pytest.raises(DependencyUnavailableError):
            _directory(lambda request, r=response: r).register_first_use(product, presentation)


@pytest.mark.parametrize("operation", ["lookup_presentation", "get_product_base_unit"])
def test_new_operations_renew_token_once(operation):
    tokens, seen = FakeTokens(), []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["authorization"])
        if len(seen) == 1:
            return httpx.Response(401)
        if request.method == "GET":
            return httpx.Response(200, json={"base_unit_id": str(uuid4())})
        return httpx.Response(200, json={"items": []})

    getattr(_directory(handler, tokens), operation)(uuid4())
    assert seen == ["Bearer tech-1", "Bearer tech-2"]
    assert tokens.invalidated == 1
