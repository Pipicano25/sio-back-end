"""Recorrido integral de la spec 021 en la pila aislada (T071; quickstart Q1, Q4, Q9 a Q12; CP-T20, SC-003).

**Compra → recepción física → inventario FIFO → actualización automática de precios → venta → descuento de
inventario**, con los servicios reales aislados (`SIO_INTEGRATION_CONTAINER_PREFIX=sio-it-`) y Keycloak aislado. No
detiene contenedores. Todos los datos son ficticios: el 19 % no es una tarifa real.

- Q1: tasa 19 %, política Público 30 %; 10 unidades a 2.000 → total 23.800 → costo real 2.380 → precio 3.094.
- Inventory recibe el costo **sin** impuesto (capa FIFO a 2.000) y la venta registra `cost_total = 2.000`.
- Q4: Mayorista 20 % se actualiza (2.856); una lista manual sin políticas no cambia.
- Auditoría en Audit con las dos identidades: el usuario que recibió y el worker técnico que aplicó el precio.
- Q9 (`TAX_NOT_ALLOWED`), Q10 (`PURCHASE_TAX_NOT_CONFIGURED`), Q11 (`403` del vendedor), Q12 (anular no revierte).

Q2, Q3, Q5 a Q8 se prueban en `CR/tests/api/test_automatic_price_*.py`, `PU/tests/api/test_cost_series.py`,
`PU/tests/integration/test_price_update_outage.py` y `test_prices_during_updates.py`.
"""

from __future__ import annotations

import time
from datetime import date
from decimal import Decimal

import pytest

from tests.integration.support import (
    AUDIT,
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    PURCHASE,
    RUN_ID,
    SALES,
    adopt_product,
    draft_body,
    new_key,
    wait_until,
)

pytestmark = pytest.mark.integration
CR = COMMERCIAL_RELATIONSHIP


def _ok(response, status=201) -> dict:
    assert response.status_code == status, response.text
    return response.json()


def _list(admin, world, code, name) -> str:
    return _ok(admin.post(f"{CR}/companies/{world.company}/price-lists", json={
        "code": f"{code}{RUN_ID}", "name": f"{name} ficticia {RUN_ID}", "currency_code": "COP",
        "valid_from": "2026-01-01T00:00:00Z",
    }))["id"]


def _policy(admin, world, price_list, markup, presentation) -> dict:
    return _ok(admin.post(f"{CR}/companies/{world.company}/price-lists/{price_list}/pricing-policies", json={
        "name": f"Política {markup} % ficticia {RUN_ID}", "markup_percentage": markup,
        "company_product_presentation_ids": [presentation],
    }))


def _prices(admin, world, price_list) -> list[dict]:
    return _ok(admin.get(f"{CR}/companies/{world.company}/price-list-items",
                         params={"price_list_id": price_list, "status": "ALL"}), 200)["items"]


def _current(admin, world, price_list) -> str | None:
    items = [item for item in _prices(admin, world, price_list) if item["status"] == "ACTIVE" and item["valid_to"] is None]
    return items[0]["unit_price"] if len(items) == 1 else None


def _balance(admin, world, product) -> Decimal:
    response = admin.get(f"{INVENTORY}/companies/{world.company}/branches/{world.branch}/balances/{product.company_product}")
    return Decimal("0") if response.status_code == 404 else Decimal(_ok(response, 200)["quantity"])


def _purchase(admin, world, product, quantity, unit_cost) -> dict:
    return _ok(admin.post(f"{PURCHASE}/companies/{world.company}/purchases", json={
        "branch_id": world.branch, "company_supplier_id": world.supplier, "operation_date": date.today().isoformat(),
        "payment_method_id": world.payment_method,
        "lines": [{"company_product_id": product.company_product, "company_product_presentation_id": product.unit_presentation,
                   "quantity": quantity, "unit_cost": unit_cost}],
    }))


def _operation(admin, world, purchase, kind, status=200, **body) -> dict:
    return _ok(admin.post(f"{PURCHASE}/companies/{world.company}/purchases/{purchase['id']}/{kind}",
                          json={"version": purchase["version"], **body}, headers={"Idempotency-Key": new_key()}), status)


def _events(admin, world, entity_type, entity_id) -> list[dict]:
    response = admin.get(f"{AUDIT}/companies/{world.company}/audit-events", params={"entity_type": entity_type})
    if response.status_code != 200:
        return []
    return [item for item in response.json()["items"] if item["entity_id"] == entity_id]


def _wait_event(admin, world, entity_type, entity_id, action) -> dict:
    found: list[dict] = []

    def arrived() -> bool:
        found[:] = [event for event in _events(admin, world, entity_type, entity_id) if event["action"] == action]
        return bool(found)

    wait_until(arrived, 120, f"{action} de {entity_type} {entity_id} no llegó a Audit")
    return found[0]


def test_purchase_receipt_fifo_automatic_price_and_sale(admin, seller, supervisor, real_world, sequence) -> None:
    world = real_world
    arroz = adopt_product(admin, world, f"ARZ{RUN_ID}")  # tasa de compra 19 % (ficticia)
    publico = _list(admin, world, "PUB", "Lista Público")
    mayorista = _list(admin, world, "MAY", "Lista Mayorista")
    manual = _list(admin, world, "DAOP", "Lista manual DAO-PRUEBAS")
    _ok(admin.post(f"{CR}/companies/{world.company}/price-list-items", json={
        "price_list_id": manual, "company_product_id": arroz.company_product,
        "company_product_presentation_id": arroz.unit_presentation, "unit_price": "13900.00",
        "valid_from": "2026-01-01T00:00:00Z",
    }))
    _policy(admin, world, publico, "30", arroz.unit_presentation)
    _policy(admin, world, mayorista, "20", arroz.unit_presentation)

    # compra y confirmación: sin cambio de existencias (spec 020)
    before = _balance(admin, world, arroz)
    draft = _purchase(admin, world, arroz, "10", "2000")
    assert draft["lines"][0]["tax_percentage"] == "19.0000" and draft["lines"][0]["tax_amount"] == "3800.00"
    assert draft["lines"][0]["total"] == "23800.00"
    confirmed = _operation(admin, world, draft, "confirmation")
    assert _balance(admin, world, arroz) == before

    # recepción física: Inventory +10 y capa FIFO a 2.000 sin impuesto
    received = _operation(admin, world, confirmed, "receipt", full_receipt_confirmed=True)
    received_at = time.monotonic()
    assert _balance(admin, world, arroz) == before + 10
    layers = _ok(admin.get(f"{INVENTORY}/companies/{world.company}/branches/{world.branch}/valuation/{arroz.company_product}/layers",
                           params={"include_closed": "true"}), 200)["items"]
    assert [layer["unit_cost"] for layer in layers] == ["2000.0000"]  # FIFO y contrato de entrada intactos

    # precio automático en menos de 1 minuto (CP-T20, SC-003)
    wait_until(lambda: _current(admin, world, publico) == "3094.00", 60, "Público no llegó a 3.094 en 60 s")
    elapsed = time.monotonic() - received_at
    assert elapsed < 60, elapsed
    wait_until(lambda: _current(admin, world, mayorista) == "2856.00", 60, "Mayorista no llegó a 2.856")
    assert [item["unit_price"] for item in _prices(admin, world, manual)] == ["13900.00"]  # Q4: la lista manual no cambia

    applications = _ok(admin.get(f"{CR}/companies/{world.company}/automatic-price-applications",
                                 params={"purchase_id": received["id"]}), 200)["items"]
    by_list = {item["price_list_id"]: item for item in applications}
    # Q1 y B-3: toda lista con política en received_at recibe una aplicación; la manual (sin políticas) ninguna. Las
    # listas con política de otras pruebas no tienen el arroz en ninguna política ni precio: NO_PRICE_TO_END.
    assert {publico, mayorista} <= set(by_list) and manual not in by_list
    assert {item["status"] for key, item in by_list.items() if key not in (publico, mayorista)} <= {"NO_PRICE_TO_END"}
    assert by_list[publico]["status"] == "APPLIED" and by_list[publico]["current_unit_cost"] == "2380"
    assert by_list[publico]["reference_cost"] == "2380" and by_list[publico]["new_price"] == "3094.00"

    # venta al precio automático y descuento de inventario con costo FIFO sin impuesto
    sale = _ok(seller.post(f"{SALES}/companies/{world.company}/sales", json=draft_body(world, {
        "company_product_id": arroz.company_product, "company_product_presentation_id": arroz.unit_presentation,
        "quantity": "1", "price_list_id": publico,
    })))
    assert sale["lines"][0]["unit_price"] == "3094.0000"
    sold = _ok(seller.post(f"{SALES}/companies/{world.company}/sales/{sale['id']}/confirmation",
                           json={"version": sale["version"]}, headers={"Idempotency-Key": new_key()}), 200)
    assert sold["status"] == "CONFIRMED" and _balance(admin, world, arroz) == before + 9
    detail = _ok(supervisor.get(f"{SALES}/companies/{world.company}/sales/{sale['id']}"), 200)["lines"][0]
    assert detail["cost_total"] == "2000.00" and detail["tax_amount"] == "0.00"
    assert detail["gross_margin_amount"] == "1094.00"  # margen de Sales: 3.094 − 2.000 (no es el recargo)

    # auditoría con ambas identidades
    receipt_event = _wait_event(admin, world, "Purchase", received["id"], "RECEIVE_PURCHASE")
    # Purchase identifica a la persona por su usuario operativo (no llena username_snapshot)
    assert receipt_event["application_user_id"] == received["received_by_user_id"]
    assert receipt_event["created_by"] and receipt_event["created_by"] != "system:commercial-relationship-price-worker"
    applied = _wait_event(admin, world, "AutomaticPriceApplication", by_list[publico]["id"], "APPLY_AUTOMATIC_PRICE")
    assert applied["username_snapshot"] == "commercial-relationship-price-worker"
    assert applied["created_by"] != receipt_event["created_by"]  # dos identidades distintas: usuario y worker técnico
    assert applied["new_values"]["new_price"] == "3094.00"
    assert applied["new_values"]["received_by_user_id"] == received["received_by_user_id"]

    # Q12: anular una compra recibida (otra, no consumida) no revierte el precio ni cambia la serie
    second = _purchase(admin, world, arroz, "10", "2000")
    second = _operation(admin, world, second, "confirmation")
    second = _operation(admin, world, second, "receipt", full_receipt_confirmed=True)
    wait_until(lambda: len(_ok(admin.get(f"{CR}/companies/{world.company}/automatic-price-applications",
                                         params={"purchase_id": second["id"], "status": "UNCHANGED"}), 200)["items"]) == 2,
               60, "La segunda recepción no quedó UNCHANGED en las dos listas")
    _operation(admin, world, second, "cancellation", reason="Anulación ficticia de validación")
    time.sleep(5)
    assert _current(admin, world, publico) == "3094.00" and _current(admin, world, mayorista) == "2856.00"
    total = _ok(admin.get(f"{CR}/companies/{world.company}/automatic-price-applications",
                          params={"price_list_id": publico}), 200)["total_records"]
    assert total == 2  # la anulación no genera solicitudes ni aplicaciones


def test_q9_sale_with_tax_is_rejected(seller, real_world) -> None:
    world = real_world
    response = seller.post(f"{SALES}/companies/{world.company}/sales", json=draft_body(world, {
        "company_product_id": world.product.company_product, "quantity": "1", "tax_amount": "100",
    }))
    assert response.status_code == 422, response.text
    assert "TAX_NOT_ALLOWED" in response.text


def test_q10_purchase_without_tax_rate_is_not_confirmed(admin, real_world, sequence) -> None:
    world = real_world
    untaxed = adopt_product(admin, world, f"SIT{RUN_ID}", purchase_tax=None)
    draft = _purchase(admin, world, untaxed, "1", "1000")
    assert draft["lines"][0]["warnings"] == ["PURCHASE_TAX_NOT_CONFIGURED"]
    response = admin.post(f"{PURCHASE}/companies/{world.company}/purchases/{draft['id']}/confirmation",
                          json={"version": draft["version"]}, headers={"Idempotency-Key": new_key()})
    assert response.status_code == 409 and response.json()["code"].endswith("PURCHASE_TAX_NOT_CONFIGURED"), response.text
    current = _ok(admin.get(f"{PURCHASE}/companies/{world.company}/purchases/{draft['id']}"), 200)
    assert current["status"] == "DRAFT"  # el borrador se conserva


def test_q11_the_seller_cannot_see_costs_or_policies(seller, real_world) -> None:
    world = real_world
    assert seller.get(f"{CR}/companies/{world.company}/automatic-price-applications").status_code == 403
    assert seller.get(f"{CR}/companies/{world.company}/price-lists/{world.price_list}/pricing-policies").status_code == 403
