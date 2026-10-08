"""Adaptadores de Product Catalog y Party Identity (T017).

Product Catalog: presentación global, producto global y unidad. Party Identity:
`identification_type` e `identification_number` de personas y organizaciones (ampliaciones
documentales C-01 de la 014 y de la 015).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from sales_service.application.exceptions import DependencyUnavailableError
from sales_service.infrastructure.party_identity_directory import HTTPPartyDirectory
from sales_service.infrastructure.product_catalog_directory import HTTPCatalogDirectory
from tests.contract.adapter_support import Recorder, Tokens, json_response, timeout


def test_product_catalog() -> None:
    presentation, product, unit = uuid4(), uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/presentations/" in path:
            return httpx.Response(200, json={"code": "CAJA12", "name": "Caja x12", "base_quantity": "12.0000"})
        if "/products/" in path:
            return httpx.Response(200, json={"base_unit_id": str(unit)})
        return httpx.Response(200, json={"code": "UND"})

    recorder = Recorder(handler)
    catalog = HTTPCatalogDirectory(base_url="http://pc.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=recorder.transport)
    assert catalog.get_presentation(presentation).base_quantity == Decimal("12")
    assert catalog.get_product(product).base_unit_id == unit
    assert catalog.get_unit(unit).code == "UND"
    assert [request.url.path for request in recorder.requests] == [
        f"/api/v1/presentations/{presentation}",
        f"/api/v1/products/{product}",
        f"/api/v1/units-of-measure/{unit}",
    ]


def test_party_identity_reads_identification() -> None:
    organization = uuid4()
    recorder = Recorder(json_response(200, {"id": str(organization), "identification_type": "NIT", "identification_number": "900123456", "legal_name": "X"}))
    party = HTTPPartyDirectory(base_url="http://pi.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=recorder.transport)
    info = party.get_organization(organization)
    assert (info.identification_type, info.identification_number) == ("NIT", "900123456")
    assert recorder.requests[0].url.path == f"/api/v1/organization-identities/{organization}"


def test_party_identity_missing_identification_is_an_existing_organization() -> None:
    """La identidad existe aunque no tenga identificación; el servicio de aplicación decide `409` (C-01)."""
    for body in ({"legal_name": "X"}, {"identification_type": "NIT", "identification_number": "  "}):
        party = HTTPPartyDirectory(base_url="http://pi.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=httpx.MockTransport(json_response(200, body)))
        info = party.get_organization(uuid4())
        assert info is not None and (info.identification_type is None or info.identification_number is None)
    party = HTTPPartyDirectory(base_url="http://pi.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=httpx.MockTransport(json_response(200, {"identification_type": 5})))
    with pytest.raises(DependencyUnavailableError) as error:  # formato inesperado → error técnico
        party.get_organization(uuid4())
    assert error.value.provider == "party-identity"


def test_party_identity_reads_person_identification() -> None:
    """C-01 (015): tipo y número de identificación de personas garantizados documentalmente."""
    person = uuid4()
    recorder = Recorder(json_response(200, {"id": str(person), "identification_type": "CC",
                                            "identification_number": "1020304050", "first_name": "Ana", "last_name": "P"}))
    party = HTTPPartyDirectory(base_url="http://pi.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=recorder.transport)
    info = party.get_person(person)
    assert (info.identification_type, info.identification_number) == ("CC", "1020304050")
    assert recorder.requests[0].url.path == f"/api/v1/person-identities/{person}"


@pytest.mark.parametrize(
    ("factory", "call", "provider"),
    [
        (lambda t: HTTPCatalogDirectory(base_url="http://pc.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=t), lambda d: d.get_unit(uuid4()), "product-catalog"),
        (lambda t: HTTPPartyDirectory(base_url="http://pi.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=t), lambda d: d.get_organization(uuid4()), "party-identity"),
        (lambda t: HTTPPartyDirectory(base_url="http://pi.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=t), lambda d: d.get_person(uuid4()), "party-identity"),
    ],
)
@pytest.mark.parametrize("handler", [json_response(500), json_response(403), timeout])
def test_unavailable(factory, call, provider, handler) -> None:
    with pytest.raises(DependencyUnavailableError) as error:
        call(factory(httpx.MockTransport(handler)))
    assert error.value.provider == provider


def test_404_is_none() -> None:
    transport = httpx.MockTransport(json_response(404))
    assert HTTPCatalogDirectory(base_url="http://pc.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=transport).get_presentation(uuid4()) is None
    assert HTTPPartyDirectory(base_url="http://pi.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=transport).get_organization(uuid4()) is None
    assert HTTPPartyDirectory(base_url="http://pi.test/api/v1", timeout_seconds=1, tokens=Tokens(), transport=transport).get_person(uuid4()) is None
