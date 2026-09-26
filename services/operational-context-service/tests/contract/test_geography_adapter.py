"""Adaptador HTTP de Geography (FR-042, FR-043, R-03, R-06).

Contrato: `specs/004-operational-context-core/contracts/geography-dependency.md`.
"""

import logging
from uuid import uuid4

import httpx
import pytest

from operational_context_service.application.exceptions import DependencyUnavailableError
from operational_context_service.infrastructure.geography_directory import HTTPGeographyDirectory
from operational_context_service.observability import (
    SERVICE_LOGGER,
    configure_logging,
    reset_trace_id,
    set_trace_id,
)

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
TOKEN = "Bearer token-secreto-del-usuario"


@pytest.fixture(autouse=True)
def trace_context():
    configure_logging()
    token = set_trace_id(TRACE_ID)
    yield
    reset_trace_id(token)


def _adapter(handler, timeout=1.0):
    return HTTPGeographyDirectory(
        base_url="http://geography.test",
        authorization=TOKEN,
        timeout_seconds=timeout,
        transport=httpx.MockTransport(handler),
    )


def test_country_ok_and_headers():
    country_id = uuid4()
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(200, json={"id": str(country_id), "status": "INACTIVE", "name": "X"})

    result = _adapter(handler).get_country(country_id)

    assert result.status == "INACTIVE"
    assert str(seen["request"].url) == f"http://geography.test/global-countries/{country_id}"
    assert seen["request"].headers["authorization"] == TOKEN
    assert seen["request"].headers["traceparent"].split("-")[1] == TRACE_ID


def test_division_returns_country():
    division_id, country_id = uuid4(), uuid4()

    def handler(request):
        assert request.url.path == f"/global-administrative-divisions/{division_id}"
        return httpx.Response(200, json={"id": str(division_id), "status": "ACTIVE", "country_id": str(country_id)})

    result = _adapter(handler).get_administrative_division(division_id)

    assert result.country_id == country_id and result.status == "ACTIVE"


@pytest.mark.parametrize("with_division", [True, False])
def test_city_returns_country_and_division(with_division):
    city_id, country_id, division_id = uuid4(), uuid4(), uuid4()

    def handler(request):
        assert request.url.path == f"/global-cities/{city_id}"
        return httpx.Response(200, json={
            "id": str(city_id),
            "status": "ACTIVE",
            "country_id": str(country_id),
            "administrative_division_id": str(division_id) if with_division else None,
        })

    result = _adapter(handler).get_city(city_id)

    assert result.country_id == country_id
    assert result.administrative_division_id == (division_id if with_division else None)


@pytest.mark.parametrize("operation", ["get_country", "get_administrative_division", "get_city"])
def test_404_returns_none(operation):
    assert getattr(_adapter(lambda request: httpx.Response(404)), operation)(uuid4()) is None


def _assert_log(caplog, cause, level):
    records = [r for r in caplog.records if r.name == SERVICE_LOGGER and cause in r.getMessage()]
    assert records, f"No se registró la causa {cause}"
    assert records[-1].levelno == level
    assert records[-1].trace_id == TRACE_ID
    assert "token-secreto" not in records[-1].getMessage()


@pytest.mark.parametrize("operation", ["get_country", "get_administrative_division", "get_city"])
@pytest.mark.parametrize("status", [401, 403])
def test_denied(caplog, operation, status):
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)

    with pytest.raises(DependencyUnavailableError) as error:
        getattr(_adapter(lambda request: httpx.Response(status)), operation)(uuid4())

    assert error.value.cause == "GEOGRAPHY_VALIDATION_DENIED"
    assert error.value.operation == operation
    _assert_log(caplog, "GEOGRAPHY_VALIDATION_DENIED", logging.WARNING)


@pytest.mark.parametrize(
    "operation, handler",
    [
        ("get_country", lambda request: httpx.Response(503)),
        ("get_country", lambda request: httpx.Response(422)),
        ("get_country", lambda request: httpx.Response(200, json={"id": "x"})),
        ("get_administrative_division", lambda request: httpx.Response(200, json={"status": "ACTIVE"})),
        ("get_city", lambda request: httpx.Response(200, json={"status": "ACTIVE", "country_id": str(uuid4())})),
        ("get_city", lambda request: httpx.Response(200, content=b"<html>")),
    ],
    ids=["503", "422", "sin-status", "division-sin-pais", "ciudad-sin-division", "no-json"],
)
def test_unexpected(caplog, operation, handler):
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)

    with pytest.raises(DependencyUnavailableError) as error:
        getattr(_adapter(handler), operation)(uuid4())

    assert error.value.cause == "GEOGRAPHY_UNAVAILABLE"
    _assert_log(caplog, "GEOGRAPHY_UNAVAILABLE", logging.ERROR)


@pytest.mark.parametrize("exception", [httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError])
def test_timeout_and_network(caplog, exception):
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)

    def handler(request):
        raise exception("fallo", request=request)

    with pytest.raises(DependencyUnavailableError) as error:
        _adapter(handler).get_city(uuid4())

    assert error.value.cause == "GEOGRAPHY_UNAVAILABLE"
    _assert_log(caplog, "GEOGRAPHY_UNAVAILABLE", logging.ERROR)


def test_uses_configured_timeout(monkeypatch):
    captured = {}
    original = httpx.Client.__init__

    def spy(self, *args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        original(self, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", spy)
    _adapter(lambda request: httpx.Response(404), timeout=3.0).get_country(uuid4())

    assert captured["timeout"] == 3.0
