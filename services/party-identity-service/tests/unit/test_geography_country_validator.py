"""Pruebas del adaptador HTTP de Geography con `httpx.MockTransport` (FR-040–FR-043, R-12)."""

import logging
from uuid import UUID, uuid4

import httpx
import pytest

from party_identity_service.application.exceptions import (
    COUNTRY_VALIDATION_DENIED,
    GEOGRAPHY_UNAVAILABLE,
    CountryNotFoundError,
    DependencyUnavailableError,
)
from party_identity_service.infrastructure.geography_country_validator import (
    HTTPGeographyCountryValidator,
)
from party_identity_service.observability import reset_trace_id, set_trace_id

BASE_URL = "http://geography.test"
COUNTRY_ID = uuid4()


def _validator(handler, *, authorization="Bearer user-token", timeout=2.5):
    return HTTPGeographyCountryValidator(
        base_url=BASE_URL,
        authorization=authorization,
        timeout_seconds=timeout,
        transport=httpx.MockTransport(handler),
    )


def _status(code: int, json=None):
    return lambda request: httpx.Response(code, json=json or {})


def test_exists_true_on_200() -> None:
    assert _validator(_status(200)).exists(COUNTRY_ID) is True


def test_exists_false_on_404() -> None:
    assert _validator(_status(404)).exists(COUNTRY_ID) is False


@pytest.mark.parametrize("code", [401, 403])
def test_denied_is_unavailable_with_internal_cause(code: int, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="party_identity_service")

    with pytest.raises(DependencyUnavailableError) as error:
        _validator(_status(code)).exists(COUNTRY_ID)

    assert error.value.cause == COUNTRY_VALIDATION_DENIED
    assert error.value.code == "DEPENDENCY_UNAVAILABLE"
    assert COUNTRY_VALIDATION_DENIED not in error.value.message
    assert any(COUNTRY_VALIDATION_DENIED in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize("code", [400, 500, 502])
def test_unexpected_status_is_unavailable(code: int, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="party_identity_service")

    with pytest.raises(DependencyUnavailableError) as error:
        _validator(_status(code)).exists(COUNTRY_ID)

    assert error.value.cause == GEOGRAPHY_UNAVAILABLE
    assert any(GEOGRAPHY_UNAVAILABLE in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize(
    "exception",
    [httpx.ConnectError("sin red"), httpx.ReadTimeout("tiempo agotado")],
)
def test_network_errors_are_unavailable(exception) -> None:
    def handler(request):
        raise exception

    with pytest.raises(DependencyUnavailableError) as error:
        _validator(handler).exists(COUNTRY_ID)

    assert error.value.cause == GEOGRAPHY_UNAVAILABLE


def test_sends_authorization_traceparent_and_uses_timeout() -> None:
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers.get("authorization")
        seen["traceparent"] = request.headers.get("traceparent")
        seen["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json={})

    token = set_trace_id("4bf92f3577b34da6a3ce929d0e0e4736")
    try:
        _validator(handler, timeout=2.5).exists(COUNTRY_ID)
    finally:
        reset_trace_id(token)

    assert seen["url"] == f"{BASE_URL}/global-countries/{COUNTRY_ID}"
    assert seen["authorization"] == "Bearer user-token"
    assert seen["traceparent"].startswith("00-4bf92f3577b34da6a3ce929d0e0e4736-")
    assert seen["timeout"]["connect"] == 2.5


def test_find_id_by_iso3_returns_single_match() -> None:
    country_id = uuid4()

    def handler(request: httpx.Request):
        assert request.url.params["iso3_code"] == "COL"
        return httpx.Response(200, json={"items": [{"id": str(country_id), "iso3_code": "COL"}]})

    assert _validator(handler).find_id_by_iso3("COL") == country_id


@pytest.mark.parametrize("count", [0, 2])
def test_find_id_by_iso3_requires_exactly_one(count: int) -> None:
    items = [{"id": str(uuid4()), "iso3_code": "COL"} for _ in range(count)]

    with pytest.raises(CountryNotFoundError):
        _validator(_status(200, {"items": items})).find_id_by_iso3("COL")


def test_find_id_by_iso3_failure_is_unavailable() -> None:
    with pytest.raises(DependencyUnavailableError):
        _validator(_status(503)).find_id_by_iso3("COL")


def test_returns_uuid_type() -> None:
    country_id = uuid4()
    validator = _validator(_status(200, {"items": [{"id": str(country_id), "iso3_code": "COL"}]}))

    assert isinstance(validator.find_id_by_iso3("col"), UUID)
