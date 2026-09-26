"""Adaptador de Party Identity con `httpx.MockTransport` (RC-13, R-16)."""

from uuid import uuid4

import httpx
import pytest

from product_catalog_service.application.exceptions import (
    ManufacturerDirectoryAccessDeniedError,
    ManufacturerDirectoryUnavailableError,
)
from product_catalog_service.infrastructure.party_identity_manufacturer_directory import (
    HTTPPartyIdentityManufacturerDirectory,
)

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"


def _directory(handler) -> HTTPPartyIdentityManufacturerDirectory:
    return HTTPPartyIdentityManufacturerDirectory(
        base_url="http://party-identity.test/",
        authorization="Bearer user-token",
        trace_id=TRACE_ID,
        timeout_seconds=2.5,
        transport=httpx.MockTransport(handler),
    )


def test_200_means_exists_and_propagates_headers() -> None:
    organization_id = uuid4()
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers.get("authorization")
        seen["traceparent"] = request.headers.get("traceparent")
        seen["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json={"id": str(organization_id)})

    assert _directory(handler).exists(organization_id) is True
    assert seen["url"] == f"http://party-identity.test/organization-identities/{organization_id}"
    assert seen["authorization"] == "Bearer user-token"
    assert seen["traceparent"].startswith(f"00-{TRACE_ID}-")
    assert seen["timeout"]["read"] == 2.5


def test_404_means_not_found() -> None:
    assert _directory(lambda request: httpx.Response(404)).exists(uuid4()) is False


@pytest.mark.parametrize("status_code", [401, 403])
def test_auth_errors_mean_access_denied(status_code: int) -> None:
    with pytest.raises(ManufacturerDirectoryAccessDeniedError):
        _directory(lambda request: httpx.Response(status_code)).exists(uuid4())


@pytest.mark.parametrize("status_code", [400, 500, 502, 503])
def test_other_statuses_mean_unavailable(status_code: int) -> None:
    with pytest.raises(ManufacturerDirectoryUnavailableError):
        _directory(lambda request: httpx.Response(status_code)).exists(uuid4())


@pytest.mark.parametrize(
    "error",
    [httpx.ReadTimeout("timeout"), httpx.ConnectError("refused")],
)
def test_network_errors_mean_unavailable(error: Exception) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    with pytest.raises(ManufacturerDirectoryUnavailableError):
        _directory(handler).exists(uuid4())
