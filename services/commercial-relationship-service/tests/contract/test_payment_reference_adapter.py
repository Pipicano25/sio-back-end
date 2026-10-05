"""Adaptador de Payment Reference con `httpx.MockTransport` (T008; R-08; RC-08).

Contrato: `specs/010-commercial-relationship-commercial-product/contracts/payment-reference-dependency.md`.
"""

from __future__ import annotations

import logging
from uuid import uuid4

import httpx
import pytest

from commercial_relationship_service.application.exceptions import (
    PAYMENT_REFERENCE_ACCESS_DENIED,
    PAYMENT_REFERENCE_UNREACHABLE,
    DependencyUnavailableError,
)
from commercial_relationship_service.infrastructure.payment_reference_directory import (
    HTTPPaymentReferenceDirectory,
)
from commercial_relationship_service.observability import reset_trace_id, set_trace_id


class FakeTokens:
    def __init__(self, fail: bool = False) -> None:
        self.issued = 0
        self.invalidated = 0
        self.fail = fail

    def get_token(self) -> str:
        if self.fail:
            raise DependencyUnavailableError(
                provider="product-catalog", cause="KEYCLOAK_TOKEN_REJECTED", operation="client_credentials_token"
            )
        self.issued += 1
        return f"tech-{self.issued}"

    def invalidate(self) -> None:
        self.invalidated += 1


def _directory(handler, tokens=None) -> HTTPPaymentReferenceDirectory:
    return HTTPPaymentReferenceDirectory(
        base_url="http://pr.test",
        timeout_seconds=1.0,
        token_client=tokens or FakeTokens(),
        transport=httpx.MockTransport(handler),
    )


def _type(type_id, code="CREDIT", status="ACTIVE"):
    return {"id": str(type_id), "code": code, "name": "Crédito", "status": status, "version": 1}


def test_get_uses_url_without_api_prefix_technical_token_and_trace():
    type_id = uuid4()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["trace"] = request.headers.get("traceparent")
        return httpx.Response(200, json=_type(type_id))

    token = set_trace_id("0af7651916cd43dd8448eb211c80319c")
    try:
        ref = _directory(handler).get_condition_type(type_id)
    finally:
        reset_trace_id(token)

    assert seen["url"] == f"http://pr.test/global-payment-condition-types/{type_id}"
    assert seen["auth"] == "Bearer tech-1"
    assert seen["trace"].startswith("00-0af7651916cd43dd8448eb211c80319c-")
    assert (ref.id, ref.code, ref.status) == (type_id, "CREDIT", "ACTIVE")


def test_inactive_and_not_found():
    type_id = uuid4()
    ref = _directory(lambda request: httpx.Response(200, json=_type(type_id, "CASH", "INACTIVE"))).get_condition_type(type_id)
    assert (ref.code, ref.status) == ("CASH", "INACTIVE")
    assert _directory(lambda request: httpx.Response(404, json={"detail": "x"})).get_condition_type(type_id) is None


def test_401_renews_token_and_retries_once():
    tokens, seen = FakeTokens(), []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["authorization"])
        return httpx.Response(401) if len(seen) == 1 else httpx.Response(200, json=_type(uuid4()))

    _directory(handler, tokens).get_condition_type(uuid4())
    assert seen == ["Bearer tech-1", "Bearer tech-2"]
    assert tokens.invalidated == 1


@pytest.mark.parametrize("statuses", [(401, 401), (403,)])
def test_second_401_or_403_is_unavailable_with_access_denied_cause(statuses, caplog):
    responses = iter(statuses)

    with caplog.at_level(logging.ERROR), pytest.raises(DependencyUnavailableError) as error:
        _directory(lambda request: httpx.Response(next(responses))).get_condition_type(uuid4())

    assert error.value.provider == "payment-reference"
    assert error.value.cause == PAYMENT_REFERENCE_ACCESS_DENIED
    assert PAYMENT_REFERENCE_ACCESS_DENIED in caplog.text
    assert "tech-" not in caplog.text  # nunca se registran tokens


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(422, json={"detail": []}),
        httpx.Response(500),
        httpx.Response(503, json={"detail": "base no disponible"}),
        httpx.Response(200, json={"id": "x", "name": "Sin código ni estado"}),
        httpx.Response(200, json={"code": "CREDIT", "status": "UNKNOWN"}),
        httpx.Response(200, content=b"no-json"),
    ],
)
def test_unexpected_responses_are_unavailable(response):
    with pytest.raises(DependencyUnavailableError) as error:
        _directory(lambda request: response).get_condition_type(uuid4())

    assert error.value.provider == "payment-reference"
    assert error.value.cause == PAYMENT_REFERENCE_UNREACHABLE


@pytest.mark.parametrize("exception", [httpx.ConnectError("x"), httpx.ReadTimeout("x")])
def test_network_errors(exception):
    def handler(request):
        raise exception

    with pytest.raises(DependencyUnavailableError) as error:
        _directory(handler).get_condition_type(uuid4())

    assert error.value.provider == "payment-reference"


def test_token_failure_is_reported_as_payment_reference():
    with pytest.raises(DependencyUnavailableError) as error:
        _directory(lambda request: httpx.Response(200), FakeTokens(fail=True)).get_condition_type(uuid4())

    assert error.value.provider == "payment-reference"
    assert error.value.cause == "KEYCLOAK_TOKEN_REJECTED"
