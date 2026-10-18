"""Adaptador de Product Catalog (T064): PC-1, PC-2 en sus dos modos y PC-3."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.ports import CatalogFilters
from product_inventory_query_service.infrastructure.product_catalog import HTTPProductCatalog
from tests.contract.adapter_support import Recorder, technical


def _pc(responder) -> tuple[HTTPProductCatalog, Recorder]:
    recorder = Recorder(responder)
    return HTTPProductCatalog(technical("product-catalog", recorder)), recorder


def test_summaries_skip_not_found_and_parse_fields() -> None:
    found, missing, brand, unit, category = (uuid4() for _ in range(5))
    pc, _ = _pc(lambda r: httpx.Response(200, json={"items": [
        {"id": str(found), "found": True, "canonical_name": "Crema", "product_type": "GOOD", "status": "ACTIVE",
         "brand": {"id": str(brand), "code": "COL", "name": "Colgate"},
         "base_unit": {"id": str(unit), "code": "UND", "name": "Unidad"},
         "categories": [{"id": str(category), "code": "ORAL", "name": "Oral", "is_primary": True}],
         "identifiers": [{"type": "GTIN", "value": "7702", "is_primary": True, "global_product_presentation_id": None}],
         "has_image": True, "image_url": "https://pc.test/api/v1/public/product-images?ref=abc"},
        {"id": str(missing), "found": False},
    ]}))
    summaries = asyncio.run(pc.summaries([found, missing]))
    assert set(summaries) == {found}
    summary = summaries[found]
    assert summary.brand.code == "COL" and summary.base_unit.code == "UND"
    assert summary.categories[0].is_primary and summary.identifiers[0].value == "7702"
    assert summary.has_image and summary.image_url.endswith("ref=abc")


def test_match_evaluator_and_conductor_bodies() -> None:
    brand, candidate = uuid4(), uuid4()
    position = {"k": ["crema"], "id": str(candidate)}

    def responder(request):
        body = json.loads(request.content)
        if "candidate_ids" in body:
            return httpx.Response(200, json={"ids": [str(candidate)]})
        return httpx.Response(200, json={"items": [{"id": str(candidate), "position": position}], "has_more": False})

    pc, recorder = _pc(responder)
    filters = CatalogFilters(brand_ids=(brand,), has_image=True, status="ACTIVE")
    assert asyncio.run(pc.match_candidates(filters, [candidate, candidate])) == [candidate]
    page, has_more = asyncio.run(pc.match_page(filters, limit=40, after={"k": ["a"], "id": str(uuid4())}))
    assert page == [(candidate, position)] and has_more is False
    evaluator, conductor = recorder.bodies()
    assert evaluator == {"status": "ACTIVE", "brand_ids": [str(brand)], "has_image": True, "candidate_ids": [str(candidate)]}
    assert conductor["limit"] == 40 and "after" in conductor and "candidate_ids" not in conductor


def test_units_and_errors() -> None:
    unit = uuid4()
    pc, _ = _pc(lambda r: httpx.Response(200, json={"items": [
        {"id": str(unit), "found": True, "status": "ACTIVE", "code": "TAB", "name": "Tableta",
         "measurement_type": "UNIT", "allows_decimals": False}]}))
    assert asyncio.run(pc.units([unit]))[unit].code == "TAB"
    pc, _ = _pc(lambda r: httpx.Response(200, json={"ids": "no-es-lista"}))
    with pytest.raises(DependencyUnavailableError):
        asyncio.run(pc.match_candidates(CatalogFilters(), [uuid4()]))


def test_presentations_lookup_parses_code_name_and_factor_and_skips_not_found() -> None:
    """`presentations/batch-lookup` (existente, spec 021): código, nombre y factor de las presentaciones globales."""
    found, missing, product = uuid4(), uuid4(), uuid4()
    pc, recorder = _pc(lambda r: httpx.Response(200, json={"items": [
        {"id": str(found), "found": True, "global_product_id": str(product), "code": "CJ10", "name": "Caja x 10",
         "status": "ACTIVE", "eligible_for_adoption": True, "base_quantity": "10.0000", "first_used_at": None},
        {"id": str(missing), "found": False},
    ]}))
    result = asyncio.run(pc.presentations([found, missing, found]))
    assert set(result) == {found}
    assert (result[found].code, result[found].name, str(result[found].base_quantity)) == ("CJ10", "Caja x 10", "10.0000")
    assert recorder.requests[0].url.path == "/api/v1/presentations/batch-lookup"
    assert recorder.bodies() == [{"ids": [str(found), str(missing)]}]
    assert asyncio.run(pc.presentations([])) == {}


def test_presentations_lookup_invalid_body_is_503() -> None:
    pc, _ = _pc(lambda r: httpx.Response(200, json={"items": [{"id": str(uuid4()), "found": True}]}))
    with pytest.raises(DependencyUnavailableError):
        asyncio.run(pc.presentations([uuid4()]))
