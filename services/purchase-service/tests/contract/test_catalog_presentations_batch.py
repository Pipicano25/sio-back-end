"""Presentaciones globales por lotes en Product Catalog (spec 021, H-2).

Purchase leía cada presentación con `GET /presentations/{id}`; ahora usa `POST /presentations/batch-lookup` (hasta
100 por llamada). Estas pruebas comprueban la **equivalencia** con la consulta individual sobre un mismo catálogo
simulado: mismos datos para las encontradas, ausencia para las inexistentes, y los mismos errores técnicos.
"""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest

from purchase_service.application.exceptions import DependencyUnavailableError
from purchase_service.infrastructure.product_catalog_directory import HTTPCatalogDirectory
from tests.contract.adapter_support import Recorder, Tokens, json_response, timeout

BASE = "http://pc.test/api/v1"


class Catalog:
    """Product Catalog simulado con las dos rutas sobre los mismos datos."""

    def __init__(self, presentations: dict[UUID, dict], *, batch_with_names: bool = True) -> None:
        self.presentations = presentations
        self.batch_with_names = batch_with_names

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/api/v1/presentations/batch-lookup":
            ids = json.loads(request.content)["ids"]
            assert 1 <= len(ids) <= 100  # límite del contrato de Product Catalog
            items = []
            for value in dict.fromkeys(ids):
                data = self.presentations.get(UUID(value))
                if data is None:
                    items.append({"id": value, "found": False, "global_product_id": None, "status": None,
                                  "eligible_for_adoption": None, "base_quantity": None, "first_used_at": None})
                    continue
                item = {"id": value, "found": True, "global_product_id": str(uuid4()), "status": data["status"],
                        "eligible_for_adoption": data["status"] == "ACTIVE", "base_quantity": data["base_quantity"],
                        "first_used_at": None}
                if self.batch_with_names:
                    item |= {"code": data["code"], "name": data["name"]}
                items.append(item)
            return httpx.Response(200, json={"items": items})
        if request.method == "GET" and path.startswith("/api/v1/presentations/"):
            data = self.presentations.get(UUID(path.rsplit("/", 1)[1]))
            if data is None:
                return httpx.Response(404, json={"code": "PRODUCT_CATALOG.NOT_FOUND"})
            return httpx.Response(200, json=data)
        return httpx.Response(500)


def directory(handler) -> tuple[HTTPCatalogDirectory, Recorder]:
    recorder = Recorder(handler)
    return HTTPCatalogDirectory(base_url=BASE, timeout_seconds=1, tokens=Tokens(), transport=recorder.transport), recorder


def sample(count: int) -> dict[UUID, dict]:
    statuses = ("ACTIVE", "INACTIVE")  # Purchase no filtra por el estado global: lo decide la presentación de empresa
    return {
        uuid4(): {"code": f"P{index:03d}", "name": f"Presentación {index}", "status": statuses[index % 2],
                  "base_quantity": f"{index + 1}.50000000"}
        for index in range(count)
    }


@pytest.mark.parametrize("count", [1, 3, 100, 101, 250])
def test_batch_equals_individual_lookups(count) -> None:
    data = sample(count)
    missing = [uuid4(), uuid4()]
    ids = [*data, *missing]
    catalog, _ = directory(Catalog(data))

    individual = {value: info for value in ids if (info := catalog.get_presentation(value)) is not None}
    batched = catalog.lookup_presentations(ids)

    assert batched == individual
    assert set(batched) == set(data)  # las inexistentes no aparecen, igual que el 404 individual
    assert all(isinstance(info.base_quantity, Decimal) for info in batched.values())


@pytest.mark.parametrize(("count", "calls"), [(1, 1), (100, 1), (101, 2), (250, 3)])
def test_one_call_per_100_presentations(count, calls) -> None:
    data = sample(count)
    catalog, recorder = directory(Catalog(data))
    catalog.lookup_presentations([*data, *data])  # los repetidos se envían una sola vez
    assert [(request.method, request.url.path) for request in recorder.requests] == [
        ("POST", "/api/v1/presentations/batch-lookup")
    ] * calls
    sent = [value for request in recorder.requests for value in json.loads(request.content)["ids"]]
    assert sorted(sent) == sorted(str(value) for value in data)
    assert all(request.headers["Authorization"].startswith("Bearer tecnico-") for request in recorder.requests)


def test_unrequested_items_are_ignored() -> None:
    """Solo se aceptan los identificadores pedidos (una respuesta inesperada no agrega presentaciones)."""
    wanted, intruder = uuid4(), uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [
            {"id": str(wanted), "found": True, "code": "UND", "name": "Unidad", "base_quantity": "1"},
            {"id": str(intruder), "found": True, "code": "X", "name": "X", "base_quantity": "9"},
        ]})

    catalog, _ = directory(handler)
    assert set(catalog.lookup_presentations([wanted])) == {wanted}


def test_previous_product_catalog_without_names_falls_back_to_individual_lookups() -> None:
    """Compatibilidad: si `batch-lookup` no trae `code`/`name`, el resultado sigue siendo el de la consulta individual."""
    data = sample(3)
    catalog, recorder = directory(Catalog(data, batch_with_names=False))
    expected = {value: catalog.get_presentation(value) for value in data}
    recorder.requests.clear()

    assert catalog.lookup_presentations(list(data)) == expected
    assert [request.method for request in recorder.requests] == ["POST", "GET", "GET", "GET"]


@pytest.mark.parametrize("handler", [json_response(500), json_response(403), json_response(404), timeout,
                                     json_response(200, {"items": "x"}),
                                     json_response(200, {"items": [{"id": "no-uuid", "found": True}]})])
def test_technical_errors_are_unavailable(handler) -> None:
    catalog, _ = directory(handler)
    with pytest.raises(DependencyUnavailableError) as error:
        catalog.lookup_presentations([uuid4()])
    assert error.value.provider == "product-catalog"


def test_bad_base_quantity_is_unavailable_like_the_individual_lookup() -> None:
    value = uuid4()
    data = {value: {"code": "X", "name": "X", "status": "ACTIVE", "base_quantity": "no-numero"}}
    catalog, _ = directory(Catalog(data))
    for call in (lambda: catalog.get_presentation(value), lambda: catalog.lookup_presentations([value])):
        with pytest.raises(DependencyUnavailableError) as error:
            call()
        assert error.value.provider == "product-catalog"


def test_empty_request_makes_no_call() -> None:
    catalog, recorder = directory(Catalog({}))
    assert catalog.lookup_presentations([]) == {}
    assert recorder.requests == []


# ------------------------------------------------- equivalencia en la validación de líneas de compra


class _HTTPPresentations:
    """Catálogo del resolvedor: presentaciones por HTTP (simulado); producto y unidad del doble."""

    def __init__(self, fakes, *, batch_with_names: bool) -> None:
        data = {value: {"code": info.code, "name": info.name, "status": "ACTIVE", "base_quantity": str(info.base_quantity)}
                for value, info in fakes.catalog.presentations.items()}
        self.http, self.recorder = directory(Catalog(data, batch_with_names=batch_with_names))
        self.lookup_presentations = self.http.lookup_presentations
        self.get_product = fakes.catalog.get_product
        self.get_unit = fakes.catalog.get_unit


def _resolve(fakes, lines, *, batch_with_names: bool):
    from dataclasses import replace
    from datetime import UTC, datetime

    from purchase_service.application.reference_validation import ReferenceResolver

    catalog = _HTTPPresentations(fakes, batch_with_names=batch_with_names)
    resolver = ReferenceResolver(replace(fakes.directories(), catalog=catalog), concurrency=4,
                                 clock=lambda: datetime.now(UTC))
    try:
        return resolver.resolve_lines(fakes.world.company, fakes.world.supplier, lines), catalog.recorder
    except Exception as error:  # noqa: BLE001 — se comparan los errores de ambos caminos
        return (type(error).__name__, getattr(error, "errors", None)), catalog.recorder


def test_line_snapshots_are_identical_with_batch_and_individual_lookups() -> None:
    from purchase_service.application.reference_validation import LineInput
    from tests.fakes import build_fakes, unit_presentation_of

    fakes = build_fakes()
    world = fakes.world
    extra = fakes.add_unit_presentations(world.product, 30)
    lines = [LineInput(world.product, world.presentation, world.supplier_product, Decimal("2")),
             LineInput(world.product_2, unit_presentation_of(world.product_2), None, Decimal("3")),
             *(LineInput(world.product, value, None, Decimal("1")) for value in extra)]

    batched, batch_calls = _resolve(fakes, lines, batch_with_names=True)
    individual, individual_calls = _resolve(fakes, lines, batch_with_names=False)

    assert batched == individual and len(batched) == 32
    assert [request.method for request in batch_calls.requests] == ["POST"]  # 1 consulta en lugar de 32
    assert [request.method for request in individual_calls.requests].count("GET") == 32


def test_missing_global_presentation_gives_the_same_error() -> None:
    from purchase_service.application.reference_validation import LineInput

    from tests.fakes import build_fakes

    fakes = build_fakes()
    world = fakes.world
    del fakes.catalog.presentations[fakes.cr.presentations[world.presentation].global_product_presentation_id]
    lines = [LineInput(world.product, world.presentation, None, Decimal("1"))]

    batched, _ = _resolve(fakes, lines, batch_with_names=True)
    individual, _ = _resolve(fakes, lines, batch_with_names=False)

    assert batched == individual
    assert batched[0] == "ValidationFailedError"
    assert [entry["code"] for entry in batched[1]] == ["PRESENTATION_NOT_FOUND"]
