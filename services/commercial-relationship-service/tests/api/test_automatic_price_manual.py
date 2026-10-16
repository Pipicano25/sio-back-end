"""Historia 6 de la spec 021: precios manuales en listas con políticas (T064; RC-021-11, decisión aprobada 11).

CP-18 (un precio manual rige de inmediato), CP-19 (manual y luego una recepción: rige el automático), CP-20 (15.000 →
pendiente 16.000 → manual 15.500 → al completarse rige 16.000, con el historial de las tres versiones y la auditoría
de ambas modificaciones). Datos ficticios: 10.000 por unidad con 60 % = 16.000.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.api.automatic_pricing_helpers import (
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
RECEIPT = {"line_total": "10000.00", "quantity": "1.0000"}  # 10.000 por unidad


@pytest.fixture
def supervisor(as_user):
    return as_user("supervisor.test")


@pytest.fixture
def client(as_token, service_token):
    return technical(as_token, service_token)


def change_price(client, item_id, unit_price: str):
    current = client.get(f"/api/v1/price-list-items/{item_id}").json()
    response = client.post(f"/api/v1/price-list-items/{item_id}/change-price",
                           json={"unit_price": unit_price, "version": current["version"]})
    assert response.status_code == 201, response.text
    return response.json()["item"]


def test_cp18_a_manual_price_applies_immediately(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation], markup="60")
    submit(client, world, request_body(world, **RECEIPT))
    run_worker(test_engine)
    automatic = prices(test_engine, world)[-1]
    assert automatic["origin"] == "AUTOMATIC" and current_price(test_engine, world) == D("16000.00")

    manual = change_price(supervisor, automatic["id"], "15500.00")
    assert manual["origin"] is None and current_price(test_engine, world) == D("15500.00")
    assert len(applications(test_engine)) == 1  # una ruta manual no crea ni modifica aplicaciones


def test_cp19_manual_and_then_a_receipt_ends_with_the_automatic_price(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    create_price(supervisor, company, world.price_list, world.product,
                 company_product_presentation_id=world.presentation, unit_price="15000.00")
    policy(supervisor, world, [world.presentation], markup="60")
    submit(client, world, request_body(world, **RECEIPT))
    run_worker(test_engine)
    assert current_price(test_engine, world) == D("16000.00")
    manual, automatic = prices(test_engine, world)
    assert manual["origin"] is None and manual["closure_reason"] == "AUTOMATIC_SUPERSEDED"
    assert automatic["origin"] == "AUTOMATIC"


def test_cp20_manual_change_while_an_application_is_pending(supervisor, client, company, fake_catalog, test_engine, outbox, clear_outbox) -> None:
    world = scenario(supervisor, company, fake_catalog)
    first = create_price(supervisor, company, world.price_list, world.product,
                         company_product_presentation_id=world.presentation, unit_price="15000.00")
    policy(supervisor, world, [world.presentation], markup="60")
    submit(client, world, request_body(world, **RECEIPT))  # pendiente: producirá 16.000
    clear_outbox()

    manual = change_price(supervisor, first["id"], "15500.00")
    assert current_price(test_engine, world) == D("15500.00")
    [pending] = applications(test_engine)
    assert pending["status"] == "PENDING"  # el cambio manual no toca la aplicación

    run_worker(test_engine)
    assert current_price(test_engine, world) == D("16000.00")
    history = prices(test_engine, world)
    assert [(row["unit_price"], row["origin"]) for row in history] == [
        (D("15000.00"), None), (D("15500.00"), None), (D("16000.00"), "AUTOMATIC"),
    ]
    [done] = applications(test_engine)
    # se actúa sobre el precio vigente al procesar, aunque sea manual y posterior a la recepción
    assert done["previous_price"] == D("15500.00") and str(done["previous_price_item_id"]) == manual["id"]

    actions = [(event["action"], event["username_snapshot"]) for event in outbox()]
    assert ("CHANGE_PRICE_LIST_ITEM_PRICE", "supervisor.test") in actions
    assert ("APPLY_AUTOMATIC_PRICE", "commercial-relationship-price-worker") in actions
