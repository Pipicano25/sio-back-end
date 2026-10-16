"""Flujo real con los servicios del entorno integrado (SC-004, SC-008; RC-01, RC-04, RC-05; T079).

Ejecutar con `pytest -m integration` con la plataforma levantada (Keycloak reconstruido con el
cliente `sales-service` y la matriz C-08). Datos ficticios creados en la sesión (`support.py`);
las existencias entran con una compra real confirmada en Purchase.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.integration.support import (
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    PARTY_IDENTITY,
    SALES,
    balance,
    draft_body,
    new_key,
    stock_with_purchase,
)

pytestmark = pytest.mark.integration
PROFITABILITY = ("unit_cost_snapshot", "cost_total", "cost_known", "gross_margin_amount", "gross_margin_percentage")


def url(world, suffix: str = "") -> str:
    return f"{SALES}/companies/{world.company}{suffix}"


def create(seller, world, *lines, **extra) -> dict:
    response = seller.post(url(world, "/sales"), json=draft_body(world, *lines, **extra))
    assert response.status_code == 201, response.text
    return response.json()


def confirm(client, world, sale, key=None):
    return client.post(
        url(world, f"/sales/{sale['id']}/confirmation"),
        json={"version": sale["version"]},
        headers={"Idempotency-Key": key or new_key()},
    )


def cancel(client, world, sale, key=None, reason="Anulación ficticia de validación"):
    return client.post(
        url(world, f"/sales/{sale['id']}/cancellation"),
        json={"version": sale["version"], "reason": reason},
        headers={"Idempotency-Key": key or new_key()},
    )


def value_of(admin, world, product) -> Decimal:
    items = admin.get(
        f"{INVENTORY}/companies/{world.company}/branches/{world.branch}/balances",
        params={"company_product_id": product.company_product},
    ).raise_for_status().json()["items"]
    return Decimal(items[0].get("inventory_value", "0")) if items else Decimal("0")


def test_purchase_stock_sale_balance_and_cancellation(admin, seller, supervisor, real_world, sequence) -> None:
    """SC-008: compra → saldo → venta → saldo final → anulación con servicios reales."""
    world = real_world
    stock_with_purchase(admin, world, [(world.product, "24", "1000")])
    before_qty, before_value = balance(admin, world, world.product), value_of(admin, world, world.product)

    draft = create(
        seller, world,
        {"company_product_id": world.product.company_product, "quantity": "2",
         "company_product_presentation_id": world.product.box_presentation, "price_list_id": world.price_list},
    )
    assert draft["lines"][0]["unit_price"] == "16000.0000" and draft["lines"][0]["price_list_item_id"] == world.box_item
    assert draft["customer_identification_snapshot"] == world.customer_identification
    availability = seller.get(url(world, f"/sales/{draft['id']}/availability"))
    assert availability.status_code == 200 and availability.json()["products"][0]["required_base_quantity"] == "24.0000"

    key = new_key()
    confirmed = confirm(seller, world, draft, key)
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["status"] == "CONFIRMED" and body["number"].startswith("FV-")
    assert body["operation_date"] == body["due_date"] and body["payment_condition_code_snapshot"] == "CASH"
    assert not any(name in body["lines"][0] for name in PROFITABILITY)  # ventas.test no ve rentabilidad
    assert balance(admin, world, world.product) == before_qty - 24

    # Kardex real: la salida con su origen.
    kardex = admin.get(
        f"{INVENTORY}/companies/{world.company}/branches/{world.branch}/kardex/{world.product.company_product}",
        params={"origin_id": draft["id"]},
    ).raise_for_status().json()["items"]
    assert [item["movement_type"] for item in kardex] == ["SALE_OUTPUT"]

    # Costo FIFO real copiado sin recalcular (P-05) y visible solo con permiso (C-08).
    seen = supervisor.get(url(world, f"/sales/{draft['id']}")).json()
    line = seen["lines"][0]
    movement = kardex[0]
    assert line["unit_cost_snapshot"] == movement["unit_cost"] and line["cost_known"] is True
    assert line["cost_total"] == str(Decimal(movement["movement_value"]).quantize(Decimal("0.01")))
    assert Decimal(line["gross_margin_amount"]) == Decimal("32000.00") - Decimal(line["cost_total"])

    again = confirm(seller, world, draft, key)  # repetición idempotente con Inventory real
    assert again.status_code == 200 and again.json()["number"] == body["number"]
    assert balance(admin, world, world.product) == before_qty - 24

    cancelled = cancel(seller, world, body)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED" and cancelled.json()["number"] == body["number"]
    assert balance(admin, world, world.product) == before_qty  # SC-004: saldo restituido
    assert value_of(admin, world, world.product) == before_value  # y valor restituido


def test_insufficient_stock_with_real_inventory(seller, real_world, sequence) -> None:
    world = real_world
    draft = create(seller, world, {"company_product_id": world.product_2.company_product, "quantity": "100000"})
    response = confirm(seller, world, draft)
    assert response.status_code == 409 and response.json()["code"] == "SALES.INSUFFICIENT_STOCK"
    assert seller.get(url(world, f"/sales/{draft['id']}")).json()["status"] == "DRAFT"


def test_price_changed_with_real_commercial_relationship(admin, seller, real_world, sequence) -> None:
    """DS-05 con Commercial Relationship real: el ítem de la lista cambia de precio entre el borrador y la confirmación."""
    world = real_world
    item = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-list-items", json={
        "price_list_id": world.price_list, "company_product_id": world.product_2.company_product,
        "company_product_presentation_id": world.product_2.unit_presentation,  # spec 019: precio por presentación
        "unit_price": "8500.00", "valid_from": "2026-01-01T00:00:00Z",
    })
    assert item.status_code == 201, item.text
    draft = create(seller, world, {"company_product_id": world.product_2.company_product, "quantity": "1",
                                   "price_list_id": world.price_list})
    assert draft["lines"][0]["unit_price"] == "8500.0000" and draft["lines"][0]["price_list_item_id"] == item.json()["id"]
    changed = admin.post(
        f"{COMMERCIAL_RELATIONSHIP}/price-list-items/{item.json()['id']}/change-price",
        json={"unit_price": "8700.00", "version": item.json()["version"]},
    )
    assert changed.status_code == 201, changed.text
    response = confirm(seller, world, draft)
    assert response.status_code == 409 and response.json()["code"] == "SALES.PRICES_CHANGED", response.text
    change = response.json()["errors"][0]
    assert (change["stored"]["unit_price"], change["current"]["unit_price"]) == ("8500.0000", "8700.0000")
    assert change["current"]["price_list_item_id"] == changed.json()["item"]["id"]
    assert seller.get(url(world, f"/sales/{draft['id']}")).json()["status"] == "DRAFT"


def test_price_list_disambiguation_with_real_commercial_relationship(admin, seller, real_world) -> None:
    """P-03 contra Commercial Relationship real: lista inexistente → 422; lista inactiva → 409."""
    from uuid import uuid4

    world = real_world
    missing = seller.post(url(world, "/sales"), json=draft_body(
        world, {"company_product_id": world.product_2.company_product, "quantity": "1", "price_list_id": str(uuid4())}
    ))
    assert missing.status_code == 422 and missing.json()["errors"][0]["code"] == "PRICE_LIST_NOT_FOUND"
    inactive_list = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-lists", json={
        "code": f"INA-{uuid4().hex[:6]}", "name": "Lista ficticia inactiva", "currency_code": "COP",
    }).json()
    admin.post(f"{COMMERCIAL_RELATIONSHIP}/price-lists/{inactive_list['id']}/deactivate", json={"version": inactive_list["version"]}).raise_for_status()
    inactive = seller.post(url(world, "/sales"), json=draft_body(
        world, {"company_product_id": world.product_2.company_product, "quantity": "1", "price_list_id": inactive_list["id"]}
    ))
    assert inactive.status_code == 409 and inactive.json()["errors"][0]["code"] == "PRICE_LIST_NOT_APPLICABLE"


def test_organization_customer_identification(seller, real_world) -> None:
    sale = create(seller, real_world, company_customer_id=real_world.customer_org)
    assert sale["customer_identification_snapshot"] == real_world.customer_org_identification


def test_product_without_inventory_control_is_409(seller, real_world) -> None:
    response = seller.post(url(real_world, "/sales"), json=draft_body(
        real_world, {"company_product_id": real_world.no_control.company_product, "quantity": "1"}
    ))
    assert response.status_code == 409 and response.json()["errors"][0]["code"] == "PRODUCT_NOT_INVENTORY_CONTROLLED"


def test_branch_assignment_and_roles_with_real_tokens(admin, seller, real_world) -> None:
    other_branch = seller.post(url(real_world, "/sales"), json={**draft_body(real_world), "branch_id": real_world.branch_b})
    assert other_branch.status_code == 403 and other_branch.json()["code"] == "SALES.BRANCH_ACCESS_DENIED"
    foreign = seller.get(f"{SALES}/companies/{real_world.foreign_company}/sales")
    assert foreign.status_code == 404


def test_technical_tokens_never_write_sales(sales_technical, operator, real_world) -> None:
    for client in (sales_technical, operator):
        response = client.post(url(real_world, "/sales"), json=draft_body(real_world))
        assert response.status_code == 403


def test_party_identity_guarantees_person_identification(sales_technical, real_world) -> None:
    """Ampliación documental C-01 (015): persona con tipo y número presentes y no vacíos."""
    customer = sales_technical.get(f"{COMMERCIAL_RELATIONSHIP}/company-customers/{real_world.customer}").json()
    person = sales_technical.get(f"{PARTY_IDENTITY}/person-identities/{customer['person_identity_id']}")
    assert person.status_code == 200
    assert person.json()["identification_type"] and person.json()["identification_number"]


def test_sales_client_has_lookup_on_its_dependencies(sales_technical, real_world) -> None:
    """El cliente real `sales-service` consulta sin membresía con `platform:lookup`."""
    assert sales_technical.get(f"{COMMERCIAL_RELATIONSHIP}/company-customers/{real_world.customer}").status_code == 200
    assert sales_technical.get(f"{COMMERCIAL_RELATIONSHIP}/price-lists/{real_world.price_list}").status_code == 200
    lookup = sales_technical.post(
        f"{INVENTORY}/companies/{real_world.company}/branches/{real_world.branch}/balances/lookup",
        json={"company_product_ids": [real_world.product.company_product]},
    )
    assert lookup.status_code == 200
