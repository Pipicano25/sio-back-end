"""Flujo completo con servicios reales (Keycloak, OC, CR, Product Catalog, Party Identity, Payment
Reference e Inventory; T073). Ejecutar con `pytest -m integration`.

Datos ficticios de validación creados en cada ejecución (ver `support.py`).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from tests.integration.support import (
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    PARTY_IDENTITY,
    PURCHASE,
    draft_body,
    new_key,
    unit_line,
    user_client,
)

pytestmark = pytest.mark.integration


def url(world, suffix: str = "") -> str:
    return f"{PURCHASE}/companies/{world.company}{suffix}"


def balance(admin, world, product: str) -> Decimal:
    response = admin.get(f"{INVENTORY}/companies/{world.company}/branches/{world.branch}/balances/{product}")
    assert response.status_code == 200, response.text
    return Decimal(response.json()["quantity"])


def create(buyer, world, *lines, **extra) -> dict:
    response = buyer.post(url(world, "/purchases"), json=draft_body(world, *lines, **extra))
    assert response.status_code == 201, response.text
    return response.json()


def confirm(buyer, world, purchase, key=None):
    return buyer.post(
        url(world, f"/purchases/{purchase['id']}/confirmation"),
        json={"version": purchase["version"]},
        headers={"Idempotency-Key": key or new_key()},
    )


def receive(buyer, world, purchase, key=None):
    """Spec 020: la recepción física completa aplica la entrada en Inventory."""
    return buyer.post(
        url(world, f"/purchases/{purchase['id']}/receipt"),
        json={"version": purchase["version"], "full_receipt_confirmed": True},
        headers={"Idempotency-Key": key or new_key()},
    )


def cancel(buyer, world, purchase, key=None, reason="Anulación ficticia de validación"):
    return buyer.post(
        url(world, f"/purchases/{purchase['id']}/cancellation"),
        json={"version": purchase["version"], "reason": reason},
        headers={"Idempotency-Key": key or new_key()},
    )


def box_line(world, quantity="2", unit_cost="120000"):
    return {
        "company_product_id": world.product.company_product,
        "company_product_presentation_id": world.product.box_presentation,
        "supplier_product_id": world.supplier_product,
        "quantity": quantity,
        "unit_cost": unit_cost,
        "tax_amount": "45600",
    }


def test_draft_confirm_inventory_and_cancel(admin, buyer, real_world, sequence) -> None:
    world = real_world
    before = balance(admin, world, world.product.company_product)
    draft = create(buyer, world, box_line(world), supplier_payment_condition_id=world.condition, supplier_document_number="FV-INT-1")
    assert draft["supplier_identification_snapshot"] == world.identification  # Party Identity real (C-01)
    assert draft["lines"][0]["base_quantity_factor_snapshot"] == "12.00000000"
    assert draft["lines"][0]["presentation_code_snapshot"].startswith("CJ12-")
    assert draft["lines"][0]["supplier_lead_time_snapshot_hours"] == "48.50"
    assert draft["payment_condition_code_snapshot"] == "CASH" and draft["due_date"] == draft["operation_date"]
    assert draft["payment_method_code_snapshot"] == "CASH"

    confirmed = confirm(buyer, world, draft)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMED" and confirmed.json()["receipt_status"] == "PENDING"
    number = confirmed.json()["number"]
    assert re.fullmatch(rf"CP-{date.fromisoformat(draft['operation_date']):%Y%m}-\d{{6}}", number), number
    assert balance(admin, world, world.product.company_product) == before  # spec 020: confirmar no mueve inventario

    key = new_key()
    received = receive(buyer, world, confirmed.json(), key)
    assert received.status_code == 200, received.text
    body = received.json()
    assert body["receipt_status"] == "RECEIVED" and body["number"] == number
    assert balance(admin, world, world.product.company_product) == before + 24

    operation = admin.get(f"{INVENTORY}/companies/{world.company}/inventory-operations/{body['inventory_operation_id']}")
    assert operation.status_code == 200, operation.text
    movement = operation.json()["movements"][0]
    assert movement["origin_detail_id"] == draft["lines"][0]["id"]
    assert movement["quantity"] == "24.0000" and movement["unit_cost"] == "10000.0000"  # sin IVA (DS-04)
    assert operation.json()["origin_type"] == "PURCHASE" and operation.json()["origin_id"] == draft["id"]

    again = receive(buyer, world, confirmed.json(), key)  # repetición idempotente con Inventory real
    assert again.status_code == 200 and again.json()["inventory_operation_id"] == body["inventory_operation_id"]
    assert balance(admin, world, world.product.company_product) == before + 24

    cancelled = cancel(buyer, world, body)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED" and cancelled.json()["number"] == body["number"]
    assert balance(admin, world, world.product.company_product) == before
    kardex = admin.get(
        f"{INVENTORY}/companies/{world.company}/branches/{world.branch}/kardex/{world.product.company_product}",
        params={"origin_id": draft["id"]},
    ).json()["items"]
    assert [item["movement_type"] for item in kardex] == ["PURCHASE_ENTRY", "ENTRY_REVERSAL"]


def test_cancel_after_consumption_is_rejected(admin, buyer, operator, real_world, sequence) -> None:
    world = real_world
    draft = create(buyer, world, unit_line(world.product_2, "5", "800"))
    confirmed = receive(buyer, world, confirm(buyer, world, draft).json()).json()
    # FIFO consume primero las capas más antiguas: se vende todo el saldo para consumir la de esta compra.
    stock = str(balance(admin, world, world.product_2.company_product))
    sale = operator.post(f"{INVENTORY}/inventory-outputs", json={
        "operation_key": str(uuid4()), "company_id": world.company, "branch_id": world.branch, "origin_type": "SALE",
        "origin_id": str(uuid4()), "application_user_id": world.buyer_user, "correlation_id": str(uuid4()), "reason": None,
        "lines": [{"origin_detail_id": str(uuid4()), "company_product_id": world.product_2.company_product, "quantity": stock}],
    })
    assert sale.status_code == 201, sale.text
    response = cancel(buyer, world, confirmed)
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.INVENTORY_ALREADY_CONSUMED"
    current = buyer.get(url(world, f"/purchases/{draft['id']}")).json()
    assert current["status"] == "CONFIRMED"


def test_credit_condition_is_not_available_in_the_mvp(buyer, real_world) -> None:
    """Spec 020 (FR-020-08): la condición CREDIT existe en Commercial Relationship, pero no se puede usar."""
    response = buyer.post(
        url(real_world, "/purchases"),
        json=draft_body(real_world, unit_line(real_world.product_2, "1", "700"), supplier_payment_condition_id=real_world.credit_condition),
    )
    assert response.status_code == 409, response.text
    assert response.json()["errors"][0]["code"] == "PAYMENT_CONDITION_NOT_AVAILABLE"


def test_product_without_inventory_control_is_409(buyer, real_world) -> None:
    response = buyer.post(
        url(real_world, "/purchases"),
        json=draft_body(real_world, unit_line(real_world.no_control, "1", "100")),
    )
    assert response.status_code == 409, response.text
    assert response.json()["errors"][0]["code"] == "PRODUCT_NOT_INVENTORY_CONTROLLED"


def test_supplier_not_found_is_422(buyer, real_world) -> None:
    response = buyer.post(url(real_world, "/purchases"), json={**draft_body(real_world), "company_supplier_id": str(uuid4())})
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "SUPPLIER_NOT_FOUND"


def test_branch_assignment_and_roles_with_real_tokens(admin, buyer, real_world) -> None:
    world = real_world
    other_branch = buyer.post(url(world, "/purchases"), json={**draft_body(world), "branch_id": world.branch_b})
    assert other_branch.status_code == 403 and other_branch.json()["code"] == "PURCHASE.BRANCH_ACCESS_DENIED"
    with user_client("reportes.test") as reader:
        assert reader.get(url(world, "/purchases")).status_code == 200
        assert reader.post(url(world, "/purchases"), json=draft_body(world)).status_code == 403
    with user_client("ventas.test") as seller:
        assert seller.get(url(world, "/purchases")).status_code == 403
    with user_client("inventario.test") as outsider:  # no es miembro de la empresa ficticia, sin permiso
        assert outsider.get(url(world, "/purchases")).status_code == 403
    foreign = admin.get(f"{PURCHASE}/companies/{world.foreign_company}/purchases")
    assert foreign.status_code == 404


def test_technical_tokens_never_write_purchases(purchase_technical, operator, real_world) -> None:
    for client in (purchase_technical, operator):
        response = client.post(url(real_world, "/purchases"), json=draft_body(real_world))
        assert response.status_code == 403


def test_party_identity_guarantees_identification(purchase_technical, real_world) -> None:
    """Ampliación documental C-01: los campos llegan al cliente técnico de Purchase."""
    response = purchase_technical.get(f"{PARTY_IDENTITY}/organization-identities/{real_world.organization}")
    assert response.status_code == 200, response.text
    assert response.json()["identification_type"] == "NIT" and response.json()["identification_number"]


def test_commercial_relationship_platform_lookup_with_real_client(purchase_technical, real_world) -> None:
    """Escenario 18 de la 010: lectura técnica sin membresía con `platform:lookup`."""
    response = purchase_technical.get(f"{COMMERCIAL_RELATIONSHIP}/company-suppliers/{real_world.supplier}")
    assert response.status_code == 200, response.text
    batch = purchase_technical.post(
        f"{COMMERCIAL_RELATIONSHIP}/company-products/batch-lookup", json={"ids": [real_world.product.company_product]}
    )
    assert batch.status_code == 200 and batch.json()["items"][0]["found"] is True


def test_lifecycle_events_real(buyer, real_world, sequence) -> None:
    from datetime import UTC, datetime

    draft = create(buyer, real_world, unit_line(real_world.product_2, "1", "800"))
    now = datetime.now(UTC)
    for event, hours in (("ORDERED", 10), ("ARRIVED", 2)):
        response = buyer.post(
            url(real_world, f"/purchases/{draft['id']}/lifecycle-events"),
            json={"event_type": event, "occurred_at": (now - timedelta(hours=hours)).isoformat(), "source": "USER"},
        )
        assert response.status_code == 201, response.text
    timeline = buyer.get(url(real_world, f"/purchases/{draft['id']}/lifecycle-events")).json()
    assert timeline["intervals"][0]["hours"] == "8.00"
