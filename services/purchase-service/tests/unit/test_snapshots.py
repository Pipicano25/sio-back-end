"""Snapshots y consultas por valores distintos (DS-02, DS-03, FR-009, FR-047; T031)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from purchase_service.application.reference_validation import HeaderInput, LineInput, ReferenceResolver
from tests.fakes import build_fakes


def resolver(fakes, concurrency: int = 4) -> ReferenceResolver:
    return ReferenceResolver(fakes.directories(), concurrency=concurrency, clock=lambda: datetime.now(UTC))


def test_header_snapshot() -> None:
    fakes = build_fakes()
    world = fakes.world
    company = fakes.oc.companies[world.company]
    snapshot = resolver(fakes).resolve_header(
        company, HeaderInput(world.branch, world.supplier, date(2026, 10, 1), world.condition)
    )
    assert snapshot.supplier_name == "Distribuidora Ficticia S.A.S."
    assert snapshot.supplier_identification == "NIT 900123456"
    assert (snapshot.payment_condition_code, snapshot.payment_terms_days) == ("CREDIT", 30)
    assert snapshot.due_date == date(2026, 10, 31)
    assert snapshot.currency_code == "COP"


def test_identification_is_truncated_to_100() -> None:
    from dataclasses import replace

    fakes = build_fakes()
    world = fakes.world
    fakes.party.organizations[world.organization] = replace(
        fakes.party.organizations[world.organization], identification_number="9" * 120
    )
    snapshot = resolver(fakes).resolve_header(
        fakes.oc.companies[world.company], HeaderInput(world.branch, world.supplier, date(2026, 10, 1), None)
    )
    assert len(snapshot.supplier_identification) == 100


def test_line_snapshots_and_distinct_lookups() -> None:
    fakes = build_fakes()
    world = fakes.world
    lines = [
        LineInput(world.product, world.presentation, world.supplier_product, Decimal("2")),
        LineInput(world.product, world.presentation, None, Decimal("1")),
        LineInput(world.product_2, None, None, Decimal("3")),
        LineInput(world.product, None, world.supplier_product, Decimal("4")),
    ]
    snapshots = resolver(fakes).resolve_lines(world.company, world.supplier, lines)
    assert [(item.product_code, item.presentation_code, item.factor, item.unit_code) for item in snapshots] == [
        ("000045", "CAJA12", Decimal("12"), "UND"),
        ("000045", "CAJA12", Decimal("12"), "UND"),
        ("000046", None, Decimal("1"), "UND"),
        ("000045", None, Decimal("1"), "UND"),
    ]
    assert snapshots[0].lead_time_hours == Decimal("48.50") and snapshots[1].lead_time_hours is None

    calls = [name for name, _ in fakes.cr.availability.calls]
    assert calls.count("products") == 1 and calls.count("presentations") == 1
    assert calls.count("supplier_product") == 1  # un solo GET por valor distinto
    catalog_calls = [name for name, _ in fakes.catalog.availability.calls]
    assert catalog_calls.count("presentation") == 1
    assert catalog_calls.count("product") == 2  # dos productos globales distintos
    assert catalog_calls.count("unit") == 1


def test_parallel_and_sequential_give_same_result() -> None:
    fakes = build_fakes()
    world = fakes.world
    lines = [LineInput(world.product, world.presentation, None, Decimal("1")), LineInput(world.product_2, None, None, Decimal("1"))]
    assert resolver(fakes, 1).resolve_lines(world.company, world.supplier, lines) == resolver(fakes, 8).resolve_lines(
        world.company, world.supplier, lines
    )
