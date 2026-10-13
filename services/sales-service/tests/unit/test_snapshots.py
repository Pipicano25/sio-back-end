"""Snapshots, precio y consultas por valores distintos (DS-02, DS-03, FR-009, C-01; T034)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from sales_service.application.reference_validation import HeaderInput, LineInput, ReferenceResolver
from tests.fakes import build_fakes


def resolver(fakes, concurrency: int = 4) -> ReferenceResolver:
    return ReferenceResolver(fakes.directories(), concurrency=concurrency, clock=lambda: datetime.now(UTC))


def test_header_snapshot_for_a_person() -> None:
    fakes = build_fakes()
    world = fakes.world
    snapshot = resolver(fakes).resolve_header(fakes.oc.companies[world.company], HeaderInput(world.branch, world.customer))
    assert snapshot.customer_name == "Ana Ficticia Pérez"
    assert snapshot.customer_identification == "CC 1020304050"
    assert snapshot.currency_code == "COP" and snapshot.branch_timezone == "America/Bogota"
    assert ("person", world.person) in fakes.party.availability.calls


def test_header_snapshot_for_an_organization() -> None:
    fakes = build_fakes()
    world = fakes.world
    snapshot = resolver(fakes).resolve_header(fakes.oc.companies[world.company], HeaderInput(world.branch, world.customer_org))
    assert (snapshot.customer_name, snapshot.customer_identification) == ("Tiendas Ficticias S.A.S.", "NIT 900123456")


def test_identification_and_name_are_truncated() -> None:
    fakes = build_fakes()
    world = fakes.world
    fakes.party.persons[world.person] = replace(fakes.party.persons[world.person], identification_number="9" * 120)
    fakes.cr.customers[world.customer] = replace(fakes.cr.customers[world.customer], display_name="N" * 250)
    snapshot = resolver(fakes).resolve_header(fakes.oc.companies[world.company], HeaderInput(world.branch, world.customer))
    assert len(snapshot.customer_identification) == 100 and len(snapshot.customer_name) == 200


def test_line_snapshots_prices_and_distinct_lookups() -> None:
    fakes = build_fakes()
    world = fakes.world
    lines = [
        LineInput(world.product, world.presentation, world.price_list, Decimal("2")),
        LineInput(world.product, world.presentation, None, Decimal("1")),
        LineInput(world.product_2, world.unit_presentation_2, None, Decimal("3")),
    ]
    snapshots = resolver(fakes).resolve_lines(world.company, "COP", lines)
    box_list, box_default, oil = snapshots
    assert (box_list.product_code, box_list.product_name) == ("000045", "Arroz ficticio 500 g")
    assert (box_list.presentation_code, box_list.presentation_name, box_list.factor) == ("CAJA12", "Caja x12", Decimal("12"))
    assert box_list.unit_code == "UND"
    assert (box_list.unit_price, box_list.price_list_id, box_list.price_list_requested) == (
        Decimal("16000.0000"), world.price_list, True,
    )
    # Spec 019: la caja sin lista pedida usa su propio precio en la predeterminada (no 1500 × 12).
    assert (box_default.unit_price, box_default.price_list_id, box_default.price_list_requested) == (
        Decimal("18000.0000"), world.default_list, False,
    )
    assert (oil.factor, oil.presentation_code, oil.unit_price) == (Decimal("1"), "UND", Decimal("9000.0000"))
    # Una consulta por valor distinto: presentaciones globales y productos globales sin repetir.
    assert sorted(call[1] for call in fakes.catalog.availability.calls if call[0] == "presentation") == sorted(
        [world.global_presentation, world.global_unit_2]
    )
    assert len([call for call in fakes.catalog.availability.calls if call[0] == "product"]) == 2
    assert len([call for call in fakes.cr.availability.calls if call[0] == "applicable_prices"]) == 1


def test_sequential_and_parallel_lookups_give_the_same_snapshots() -> None:
    fakes = build_fakes()
    world = fakes.world
    lines = [
        LineInput(world.product, world.presentation, None, Decimal("1")),
        LineInput(world.product_2, world.unit_presentation_2, None, Decimal("1")),
    ]
    assert resolver(fakes, 1).resolve_lines(world.company, "COP", lines) == resolver(fakes, 8).resolve_lines(
        world.company, "COP", lines
    )
