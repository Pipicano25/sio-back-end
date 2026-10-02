"""Adaptador HTTP de país, división y ciudad (T028; FR-036, FR-038, RC-05)."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

import httpx
import pytest

from party_identity_service.application.exceptions import (
    COUNTRY_VALIDATION_DENIED,
    GEOGRAPHY_UNAVAILABLE,
    DependencyUnavailableError,
)
from party_identity_service.infrastructure.geography_location_directory import (
    HTTPGeographyLocationDirectory,
)
from party_identity_service.observability import reset_trace_id, set_trace_id

COUNTRY, DIVISION, CITY = uuid4(), uuid4(), uuid4()


def _directory(handler) -> HTTPGeographyLocationDirectory:
    return HTTPGeographyLocationDirectory(
        base_url="http://geography.test/",
        authorization="Bearer user-token",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )


def _json(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, content=json.dumps(body), headers={"content-type": "application/json"})


def test_reads_each_level_with_status_and_parents() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path == f"/global-countries/{COUNTRY}":
            return _json(200, {"id": str(COUNTRY), "status": "ACTIVE", "name": "COLOMBIA"})
        if path == f"/global-administrative-divisions/{DIVISION}":
            return _json(200, {"id": str(DIVISION), "status": "INACTIVE", "country_id": str(COUNTRY)})
        if path == f"/global-cities/{CITY}":
            return _json(200, {"id": str(CITY), "status": "ACTIVE", "country_id": str(COUNTRY),
                               "administrative_division_id": str(DIVISION)})
        return httpx.Response(404)

    token = set_trace_id("4bf92f3577b34da6a3ce929d0e0e4736")
    try:
        directory = _directory(handler)
        country = directory.get_country(COUNTRY)
        division = directory.get_administrative_division(DIVISION)
        city = directory.get_city(CITY)
    finally:
        reset_trace_id(token)

    assert (country.status, division.status, city.status) == ("ACTIVE", "INACTIVE", "ACTIVE")
    assert division.country_id == COUNTRY
    assert (city.country_id, city.administrative_division_id) == (COUNTRY, DIVISION)
    assert all(request.headers["authorization"] == "Bearer user-token" for request in seen)
    assert all("4bf92f3577b34da6a3ce929d0e0e4736" in request.headers["traceparent"] for request in seen)


@pytest.mark.parametrize("method", ["get_country", "get_administrative_division", "get_city"])
def test_not_found_returns_none(method: str) -> None:
    assert getattr(_directory(lambda request: httpx.Response(404)), method)(uuid4()) is None


@pytest.mark.parametrize("status", [401, 403])
def test_denied_is_dependency_unavailable_with_internal_cause(status: int, caplog) -> None:
    caplog.set_level(logging.WARNING)

    with pytest.raises(DependencyUnavailableError) as error:
        _directory(lambda request: httpx.Response(status)).get_country(COUNTRY)

    assert error.value.dependency == "geography"
    assert error.value.cause == COUNTRY_VALIDATION_DENIED
    assert COUNTRY_VALIDATION_DENIED in caplog.text


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(500),
        lambda request: httpx.Response(418),
        lambda request: _json(200, {"id": "x"}),
        lambda request: _json(200, {"id": "x", "status": "ACTIVE"}),  # división sin country_id
        lambda request: httpx.Response(200, content=b"no-json"),
    ],
)
def test_unexpected_responses_are_unavailable(handler) -> None:
    with pytest.raises(DependencyUnavailableError) as error:
        _directory(handler).get_administrative_division(DIVISION)

    assert error.value.dependency == "geography"
    assert error.value.cause == GEOGRAPHY_UNAVAILABLE


def test_network_error_and_timeout_are_unavailable() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("lento", request=request)

    def network(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("caído", request=request)

    for handler in (timeout, network):
        with pytest.raises(DependencyUnavailableError) as error:
            _directory(handler).get_city(CITY)
        assert error.value.cause == GEOGRAPHY_UNAVAILABLE
