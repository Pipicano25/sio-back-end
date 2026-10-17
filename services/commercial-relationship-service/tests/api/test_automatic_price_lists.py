"""Historia 3 de la spec 021: listas manuales protegidas y precios sin política (T048; FR-021-20, FR-021-23; DS-06).

CP-26, CP-60 (la lista manual no cambia), CP-27 y CP-68 (sin política se conserva el precio: `SKIPPED_NO_POLICY`,
aclaración del 2026-10-16, RC-021-13), CP-16 (presentación retirada), CP-59 (última política inactivada con
aplicaciones pendientes), CP-23, CP-24 y CP-58 (`SKIPPED_LIST_NOT_EFFECTIVE`). Datos ficticios.
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


def _snapshot(test_engine, world, presentation=None, price_list=None) -> list[tuple]:
    """Precio a precio: importe, vigencias, estado, motivo de cierre y versión (para comprobar que nada cambió)."""
    return [
        (row["id"], row["unit_price"], row["valid_from"], row["valid_to"], row["status"], row["closure_reason"],
         row["version"], row["updated_at"])
        for row in prices(test_engine, world, presentation, price_list)
    ]


def test_cp27_presentation_without_policy_keeps_its_prices(supervisor, client, company, fake_catalog, test_engine) -> None:
    """RC-021-13: en una lista con políticas, una presentación recibida sin política conserva vigente y futuros."""
    world = scenario(supervisor, company, fake_catalog)
    other = add_presentation(supervisor, company, fake_catalog, world)
    start = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    create_price(supervisor, company, world.price_list, world.product,
                 company_product_presentation_id=world.presentation, unit_price="3500.00",
                 valid_to=start)
    create_price(supervisor, company, world.price_list, world.product,
                 company_product_presentation_id=world.presentation, unit_price="3600.00",
                 valid_from=start)
    policy(supervisor, world, [other])  # la lista usa políticas, pero la presentación no está en ninguna
    before = _snapshot(test_engine, world)
    submit(client, world, request_body(world))
    run_worker(test_engine)

    [application] = applications(test_engine)
    assert application["status"] == "SKIPPED_NO_POLICY" and application["new_price"] is None
    assert application["cancelled_future_item_ids"] in ([], None) and application["new_price_item_id"] is None
    assert _snapshot(test_engine, world) == before  # ni importe, ni vigencias, ni versión, ni motivo de cierre
    assert current_price(test_engine, world) == D("3500.00")
    assert all(row["closure_reason"] is None and row["automatic_application_id"] is None for row in prices(test_engine, world))
    listed = supervisor.get(f"/api/v1/price-lists/{world.price_list['id']}").json()
    assert listed["status"] == "ACTIVE"


def test_without_policy_and_without_prices_is_skipped(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    other = add_presentation(supervisor, company, fake_catalog, world)
    policy(supervisor, world, [other])
    submit(client, world, request_body(world))
    run_worker(test_engine)
    [application] = applications(test_engine)
    assert application["status"] == "SKIPPED_NO_POLICY" and prices(test_engine, world) == []


def test_cp16_removed_presentation_keeps_its_price_on_the_next_receipt(supervisor, client, company, fake_catalog, test_engine) -> None:
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
    before = _snapshot(test_engine, world)
    submit(client, world, request_body(world, sequence=2, previous=("23800.00", "10.0000"), line_total="30000.00"))
    run_worker(test_engine)
    assert applications(test_engine)[-1]["status"] == "SKIPPED_NO_POLICY"
    assert _snapshot(test_engine, world) == before  # conserva el último precio automático (RC-021-13)
    assert current_price(test_engine, world) == D("3094.00")


def test_cp68_only_received_presentations_with_policy_change(supervisor, client, company, fake_catalog, test_engine) -> None:
    """Ejemplo aprobado el 2026-10-16: cinco precios, política del 30 % con Colgate y Clarityne; luego Dolex sin política."""
    world = scenario(supervisor, company, fake_catalog)
    colgate = world.presentation
    clarityne, acetaminofen, dolex, advil = (add_presentation(supervisor, company, fake_catalog, world) for _ in range(4))
    manual = create_price_list(supervisor, company, code=f"MAN-{world.price_list['code'][-4:]}")
    listed = {colgate: "13900.00", clarityne: "21900.00", acetaminofen: "8500.00", dolex: "12000.00", advil: "15000.00"}
    for presentation, amount in listed.items():
        for target in (world.price_list, manual):
            create_price(supervisor, company, target, world.product,
                         company_product_presentation_id=presentation, unit_price=amount)
    policy(supervisor, world, [colgate, clarityne], markup="30")
    untouched = {presentation: _snapshot(test_engine, world, presentation) for presentation in (acetaminofen, dolex, advil)}
    manual_before = {presentation: _snapshot(test_engine, world, presentation, manual) for presentation in listed}

    # se reciben Colgate (10 a 2.380 con impuesto → 3.094) y Clarityne (10 a 15.000 → 19.500)
    submit(client, world, request_body(world, presentation=colgate))
    submit(client, world, request_body(world, presentation=clarityne, line_total="150000.00"))
    run_worker(test_engine)
    assert current_price(test_engine, world, colgate) == D("3094.00")
    assert current_price(test_engine, world, clarityne) == D("19500.00")
    for presentation in (colgate, clarityne):  # el manual se cerró y lo sustituye el automático
        old, new = prices(test_engine, world, presentation)
        assert old["closure_reason"] == "AUTOMATIC_SUPERSEDED" and old["valid_to"] is not None
        assert new["origin"] == "AUTOMATIC" and new["valid_to"] is None
    for presentation, snapshot in untouched.items():  # no recibidos: idénticos
        assert _snapshot(test_engine, world, presentation) == snapshot

    # después llega Dolex, que no está en ninguna política: conserva 12.000 sin cambios
    submit(client, world, request_body(world, presentation=dolex, line_total="50000.00"))
    run_worker(test_engine)
    dolex_application = next(a for a in applications(test_engine) if str(a["company_product_presentation_id"]) == dolex)
    assert dolex_application["status"] == "SKIPPED_NO_POLICY"
    assert _snapshot(test_engine, world, dolex) == untouched[dolex]
    assert current_price(test_engine, world, dolex) == D("12000.00")
    for presentation in (acetaminofen, advil):
        assert _snapshot(test_engine, world, presentation) == untouched[presentation]
    # la lista manual vecina (sin políticas) no recibió aplicaciones ni cambió (RC-021-6)
    assert all(str(a["price_list_id"]) != manual["id"] for a in applications(test_engine))
    for presentation, snapshot in manual_before.items():
        assert _snapshot(test_engine, world, presentation, manual) == snapshot


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
