"""Historia 3 de la spec 021: listas manuales protegidas y precios sin política (T048; FR-021-20, FR-021-23; DS-06).

CP-26, CP-60 (la lista manual no cambia), CP-27 y `NO_PRICE_TO_END`, CP-16 (presentación retirada), CP-59 (última
política inactivada con aplicaciones pendientes), CP-23, CP-24 y CP-58 (`SKIPPED_LIST_NOT_EFFECTIVE`). Datos ficticios.
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
from tests.api.helpers import create_price, create_price_list, price_list_update_body

D = Decimal


@pytest.fixture
def supervisor(as_user):
    return as_user("supervisor.test")


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


@pytest.fixture
def client(as_token, service_token):
    return technical(as_token, service_token)


def test_cp26_without_policies_nothing_changes(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    create_price(supervisor, company, world.price_list, world.product,
                 company_product_presentation_id=world.presentation, unit_price="3500.00")
    submit(client, world, request_body(world))
    run_worker(test_engine)
    assert applications(test_engine) == []
    assert current_price(test_engine, world) == D("3500.00")


def test_cp60_manual_list_keeps_its_prices_next_to_a_policy_list(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    manual = create_price_list(supervisor, company, code="DAO-PRUEBAS-FICTICIA")
    create_price(supervisor, company, manual, world.product,
                 company_product_presentation_id=world.presentation, unit_price="13900.00")
    policy(supervisor, world, [world.presentation], markup="30")
    submit(client, world, request_body(world))
    run_worker(test_engine)
    assert current_price(test_engine, world) == D("3094.00")  # la lista con políticas se actualiza
    assert current_price(test_engine, world, price_list=manual) == D("13900.00")  # la manual no se toca
    assert len(prices(test_engine, world, price_list=manual)) == 1


def test_cp27_presentation_without_policy_loses_its_price_in_that_list_only(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    other = add_presentation(supervisor, company, fake_catalog, world)
    start = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    create_price(supervisor, company, world.price_list, world.product,
                 company_product_presentation_id=world.presentation, unit_price="3500.00",
                 valid_to=start)
    future = create_price(supervisor, company, world.price_list, world.product,
                          company_product_presentation_id=world.presentation, unit_price="3600.00",
                          valid_from=start)
    policy(supervisor, world, [other])  # la lista usa políticas, pero la presentación no está en ninguna
    submit(client, world, request_body(world))
    run_worker(test_engine)

    [application] = applications(test_engine)
    assert application["status"] == "ENDED_NO_POLICY" and application["new_price"] is None
    assert current_price(test_engine, world) is None  # sin precio vigente hasta que se registre uno manual
    rows = {str(row["id"]): row for row in prices(test_engine, world)}
    closed = next(row for key, row in rows.items() if key != future["id"])
    assert closed["valid_to"] is not None and closed["closure_reason"] == "NO_POLICY" and closed["status"] == "ACTIVE"
    assert rows[future["id"]]["status"] == "INACTIVE" and rows[future["id"]]["closure_reason"] == "NO_POLICY"
    listed = supervisor.get(f"/api/v1/price-lists/{world.price_list['id']}").json()
    assert listed["status"] == "ACTIVE"  # la lista no se desactiva


def test_no_price_to_end(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    other = add_presentation(supervisor, company, fake_catalog, world)
    policy(supervisor, world, [other])
    submit(client, world, request_body(world))
    run_worker(test_engine)
    [application] = applications(test_engine)
    assert application["status"] == "NO_PRICE_TO_END" and prices(test_engine, world) == []


def test_cp16_removed_presentation_is_ended_on_the_next_receipt(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    other = add_presentation(supervisor, company, fake_catalog, world)
    created = policy(supervisor, world, [world.presentation, other], markup="30")
    submit(client, world, request_body(world, sequence=1))
    run_worker(test_engine)
    assert current_price(test_engine, world) == D("3094.00")

    removed = supervisor.post(
        f"/api/v1/pricing-policies/{created['id']}/presentations/remove",
        json={"version": created["version"], "company_product_presentation_ids": [world.presentation]},
    )
    assert removed.status_code == 200
    assert current_price(test_engine, world) == D("3094.00")  # retirar no cambia precios (RC-021-2)
    submit(client, world, request_body(world, sequence=2, previous=("23800.00", "10.0000")))
    run_worker(test_engine)
    assert current_price(test_engine, world) is None
    assert applications(test_engine)[-1]["status"] == "ENDED_NO_POLICY"


def test_cp59_last_policy_deactivated_keeps_pending_capture_and_frees_the_list(supervisor, admin, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    created = policy(supervisor, world, [world.presentation], markup="30")
    submit(client, world, request_body(world, sequence=1))  # pendiente: aún no se procesa
    deactivated = supervisor.post(f"/api/v1/pricing-policies/{created['id']}/deactivate",
                                  json={"version": 1, "reason": "Fin de la política (ficticio)"})
    assert deactivated.status_code == 200
    run_worker(test_engine)
    assert current_price(test_engine, world) == D("3094.00")  # la pendiente usa su captura original (30 %)

    manual = supervisor.post(f"/api/v1/price-list-items/{prices(test_engine, world)[0]['id']}/change-price",
                             json={"unit_price": "5000.00", "version": 1})
    assert manual.status_code == 201, manual.text
    accepted = submit(client, world, request_body(world, sequence=2, previous=("23800.00", "10.0000")))
    assert accepted["applications"] == []  # la lista volvió a modo manual: la recepción siguiente no la toca
    run_worker(test_engine)
    assert current_price(test_engine, world) == D("5000.00")


def test_cp23_inactive_list_is_skipped(admin, supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation])
    submit(client, world, request_body(world))
    assert admin.post(f"/api/v1/price-lists/{world.price_list['id']}/deactivate", json={"version": 1}).status_code == 200
    run_worker(test_engine)
    [application] = applications(test_engine)
    assert application["status"] == "SKIPPED_LIST_NOT_EFFECTIVE" and prices(test_engine, world) == []


def test_cp24_cp58_list_out_of_validity_when_processing_is_skipped(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation])
    submit(client, world, request_body(world))
    yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    expired = supervisor.put(
        f"/api/v1/price-lists/{world.price_list['id']}",
        json=price_list_update_body(world.price_list, valid_from=(datetime.now(UTC) - timedelta(days=5)).isoformat(),
                                    valid_to=yesterday),
    )
    assert expired.status_code == 200, expired.text
    run_worker(test_engine)
    [application] = applications(test_engine)
    assert application["status"] == "SKIPPED_LIST_NOT_EFFECTIVE"
