"""Historia 2 de la spec 021 (CR): procesamiento de las aplicaciones por el worker (T038; FR-021-21..24).

CP-01 (primer precio `[now, NULL)`), CP-02 a CP-04 de punta a punta, CP-21 (`UNCHANGED` sin versión nueva y con
futuros cancelados), CP-22 y CP-50 (futuros cancelados solo de esa lista y presentación), CP-38 (presentaciones
independientes), CP-T16 (auditoría); Historia 9 (T069): CP-28 (`SKIPPED_ZERO_COST`), CP-45
(`SKIPPED_CURRENCY_MISMATCH`, sin conversión) y `SKIPPED_PRESENTATION_INACTIVE`. Ejemplo ficticio: 10 bolsas a 2.000 + 19 % de impuesto = 23.800 → 2.380 por
unidad; con 30 % el precio es 3.094.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from tests.api.automatic_pricing_helpers import (
    add_presentation,
    applications,
    current_price,
    policy,
    prices,
    request_body,
    run_worker,
    scenario,
    submit,
    technical,
)
from tests.api.helpers import create_price

D = Decimal


@pytest.fixture
def supervisor(as_user):
    return as_user("supervisor.test")


@pytest.fixture
def client(as_token, service_token):
    return technical(as_token, service_token)


def test_cp01_first_receipt_creates_the_first_automatic_price(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation], markup="30")
    submit(client, world, request_body(world, line_total="23800.00", quantity="10.0000"))
    run_worker(test_engine)

    [application] = applications(test_engine)
    assert application["status"] == "APPLIED" and application["attempts"] == 1
    assert application["current_unit_cost"] == D("2380") and application["reference_cost"] == D("2380")
    assert application["previous_price"] is None and application["new_price"] == D("3094.00")
    [price] = prices(test_engine, world)
    assert price["unit_price"] == D("3094.00") and price["valid_to"] is None and price["origin"] == "AUTOMATIC"
    assert price["automatic_application_id"] == application["id"]
    assert current_price(test_engine, world) == D("3094.00")


def test_cp02_cp03_cp04_reference_series_end_to_end(supervisor, client, company, fake_catalog, test_engine) -> None:
    """Costos reales 2.800, 2.600, 2.400 y 2.700 (tasa 0 %, 1 unidad): referencias 2.800, 2.700, 2.500 y 2.700."""
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation], markup="0")
    costs = ["2800.00", "2600.00", "2400.00", "2700.00"]
    for sequence, cost in enumerate(costs, start=1):
        previous = (costs[sequence - 2], "1.0000") if sequence > 1 else None
        submit(client, world, request_body(world, sequence=sequence, line_total=cost, quantity="1.0000", previous=previous))
        run_worker(test_engine)
        assert current_price(test_engine, world) == D(["2800", "2700", "2500", "2700"][sequence - 1])
    references = [row["reference_cost"] for row in applications(test_engine)]
    assert references == [D("2800"), D("2700"), D("2500"), D("2700")]
    history = prices(test_engine, world)
    assert [row["unit_price"] for row in history] == [D("2800"), D("2700"), D("2500"), D("2700")]
    assert all(row["closure_reason"] == "AUTOMATIC_SUPERSEDED" for row in history[:-1])  # historial conservado


def test_existing_manual_price_is_closed_and_replaced(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    manual = create_price(supervisor, company, world.price_list, world.product,
                          company_product_presentation_id=world.presentation, unit_price="3500.00")
    policy(supervisor, world, [world.presentation], markup="30")
    submit(client, world, request_body(world))
    run_worker(test_engine)
    old, new = prices(test_engine, world)
    assert str(old["id"]) == manual["id"] and old["valid_to"] is not None and old["closure_reason"] == "AUTOMATIC_SUPERSEDED"
    assert old["status"] == "ACTIVE"  # cerrado, no inactivado: el historial muestra hasta cuándo rigió
    assert new["unit_price"] == D("3094.00")
    [application] = applications(test_engine)
    assert application["previous_price"] == D("3500.00") and str(application["previous_price_item_id"]) == manual["id"]


def test_cp21_same_price_creates_no_version_but_cancels_future_prices(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    current = create_price(supervisor, company, world.price_list, world.product,
                           company_product_presentation_id=world.presentation, unit_price="3094.00",
                           valid_from=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
                           valid_to=(datetime.now(UTC) + timedelta(days=10)).isoformat())
    future = create_price(supervisor, company, world.price_list, world.product,
                          company_product_presentation_id=world.presentation, unit_price="4000.00",
                          valid_from=(datetime.now(UTC) + timedelta(days=10)).isoformat())
    policy(supervisor, world, [world.presentation], markup="30")
    submit(client, world, request_body(world))
    run_worker(test_engine)

    [application] = applications(test_engine)
    assert application["status"] == "UNCHANGED" and application["new_price"] == D("3094.00")
    assert application["new_price_item_id"] is None
    rows = {str(row["id"]): row for row in prices(test_engine, world)}
    assert len(rows) == 2  # sin versión nueva
    # Sin versión nueva, pero sin hueco: el precio vigente queda con vigencia abierta (M-2) al cancelar el futuro.
    assert rows[current["id"]]["valid_to"] is None and rows[current["id"]]["closure_reason"] is None
    assert rows[future["id"]]["status"] == "INACTIVE" and rows[future["id"]]["closure_reason"] == "AUTOMATIC_SUPERSEDED"
    assert [str(i) for i in application["cancelled_future_item_ids"]] == [future["id"]]


def test_cp22_cp50_future_prices_of_other_presentations_are_untouched(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    other = add_presentation(supervisor, company, fake_catalog, world)
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    mine = create_price(supervisor, company, world.price_list, world.product,
                        company_product_presentation_id=world.presentation, unit_price="9000.00", valid_from=tomorrow)
    theirs = create_price(supervisor, company, world.price_list, world.product,
                          company_product_presentation_id=other, unit_price="9000.00", valid_from=tomorrow)
    policy(supervisor, world, [world.presentation], markup="30")
    submit(client, world, request_body(world))
    run_worker(test_engine)

    mine_row = next(row for row in prices(test_engine, world) if str(row["id"]) == mine["id"])
    assert mine_row["status"] == "INACTIVE" and mine_row["closure_reason"] == "AUTOMATIC_SUPERSEDED"
    [theirs_row] = prices(test_engine, world, presentation=other)
    assert str(theirs_row["id"]) == theirs["id"] and theirs_row["status"] == "ACTIVE" and theirs_row["closure_reason"] is None
    # CP-50: sin solapamientos entre los precios activos de la presentación.
    active = [row for row in prices(test_engine, world) if row["status"] == "ACTIVE"]
    assert len(active) == 1 and active[0]["valid_to"] is None


def test_cp38_presentations_are_processed_independently(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    other = add_presentation(supervisor, company, fake_catalog, world)
    policy(supervisor, world, [world.presentation, other], markup="10")
    submit(client, world, request_body(world, line_total="1000.00", quantity="1.0000"))
    submit(client, world, request_body(world, presentation=other, line_total="5000.00", quantity="1.0000"))
    run_worker(test_engine)
    assert current_price(test_engine, world) == D("1100.00")
    assert current_price(test_engine, world, presentation=other) == D("5500.00")


def test_cpt16_audit_records_the_full_trace_and_both_identities(supervisor, client, company, fake_catalog, test_engine, outbox, clear_outbox) -> None:
    world = scenario(supervisor, company, fake_catalog)
    created = policy(supervisor, world, [world.presentation], markup="30")
    body = request_body(world)
    submit(client, world, body)
    clear_outbox()
    run_worker(test_engine)
    [event] = [event for event in outbox() if event["action"] == "APPLY_AUTOMATIC_PRICE"]
    values = event["new_values"]
    assert event["entity_type"] == "AutomaticPriceApplication" and event["result"] == "SUCCESS"
    assert values["purchase_id"] == body["purchase_id"] and values["purchase_detail_id"] == body["purchase_detail_id"]
    assert values["price_list_id"] == world.price_list["id"] and values["company_product_presentation_id"] == world.presentation
    assert values["policy_id"] == created["id"] and values["markup_percentage"] == "30.0000"
    assert values["current_unit_cost"] == "2380" and values["previous_unit_cost"] is None and values["reference_cost"] == "2380"
    assert values["previous_price"] is None and values["new_price"] == "3094.00"
    assert values["received_by_user_id"] == body["received_by_user_id"]  # usuario que recibió
    assert event["username_snapshot"] == "commercial-relationship-price-worker"  # identidad técnica que procesó
    assert values["attempts"] == 1 and values["completed_at"]
    assert "token" not in str(event).lower()


# ------------------------------------------------- Historia 9: casos defensivos (T069; FR-021-23)


def _with_manual_price(supervisor, client, company, fake_catalog, **world_options):
    world = scenario(supervisor, company, fake_catalog, **world_options)
    create_price(supervisor, company, world.price_list, world.product,
                 company_product_presentation_id=world.presentation, unit_price="3500.00")
    policy(supervisor, world, [world.presentation], markup="30")
    return world


def _skipped(test_engine, world, status: str) -> None:
    run_worker(test_engine)
    [application] = applications(test_engine)
    assert application["status"] == status and application["new_price"] is None
    assert application["new_price_item_id"] is None and application["cancelled_future_item_ids"] == []
    assert current_price(test_engine, world) == D("3500.00")  # el precio se conserva
    assert len(prices(test_engine, world)) == 1


def test_cp28_zero_cost_is_skipped_and_the_price_is_kept(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = _with_manual_price(supervisor, client, company, fake_catalog)
    submit(client, world, request_body(world, line_total="0.00"))  # defensivo: Purchase exige costo mayor que cero
    _skipped(test_engine, world, "SKIPPED_ZERO_COST")


def test_cp45_another_currency_is_skipped_without_conversion(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = _with_manual_price(supervisor, client, company, fake_catalog)
    submit(client, world, request_body(world, currency="USD"))
    _skipped(test_engine, world, "SKIPPED_CURRENCY_MISMATCH")


def test_inactive_presentation_is_skipped(supervisor, as_user, client, company, fake_catalog, test_engine) -> None:
    world = _with_manual_price(supervisor, client, company, fake_catalog)
    submit(client, world, request_body(world))
    admin = as_user("admin.test")
    current = admin.get(f"/api/v1/company-product-presentations/{world.presentation}").json()
    deactivated = admin.post(f"/api/v1/company-product-presentations/{world.presentation}/deactivate",
                             json={"version": current["version"]})
    assert deactivated.status_code == 200, deactivated.text
    _skipped(test_engine, world, "SKIPPED_PRESENTATION_INACTIVE")
