"""Compra en borrador (Historia 1; FR-001 a FR-014, RN-01; T029)."""

from __future__ import annotations

from datetime import UTC, datetime

from tests.conftest import base, distinct_lines, line, purchase_body, user_sub


def test_create_draft_with_lines(buyer, world, fakes) -> None:
    fakes.inventory.availability.fail_if_called = True  # RN-01: el borrador nunca toca Inventory
    body = purchase_body(
        world,
        line(world.product, "2", "120000", company_product_presentation_id=world.presentation,
             supplier_product_id=world.supplier_product),
        line(world.product_2, "3", "5000.50", discount_amount="1.50"),
        line(world.product, "1.5", "2000"),
        supplier_document_number="FV-1234",
    )
    response = buyer.post(f"{base(world)}/purchases", json=body)
    assert response.status_code == 201, response.text
    purchase = response.json()
    assert purchase["status"] == "DRAFT" and purchase["number"] is None and purchase["inventory_operation_id"] is None
    assert purchase["version"] == 1
    assert purchase["currency_code"] == "COP"
    assert purchase["created_by"] == user_sub("compras.test")
    assert purchase["created_by_user_id"] == str(fakes.oc.members[(user_sub("compras.test"), world.company)])
    assert purchase["payment_condition_code_snapshot"] == "CASH" and purchase["payment_terms_days_snapshot"] == 0
    assert purchase["due_date"] == purchase["operation_date"]
    assert purchase["supplier_name_snapshot"] == "Distribuidora Ficticia S.A.S."
    assert purchase["supplier_identification_snapshot"] == "NIT 900123456"
    assert purchase["payment_method_id"] == str(world.payment_method)
    assert (purchase["payment_method_code_snapshot"], purchase["payment_method_name_snapshot"]) == ("CASH", "Efectivo")
    assert purchase["receipt_status"] is None and purchase["received_at"] is None
    assert [item["line_number"] for item in purchase["lines"]] == [1, 2, 3]

    first, second, third = purchase["lines"]
    assert (first["subtotal"], first["tax_amount"], first["total"]) == ("240000.00", "45600.00", "285600.00")
    assert first["base_quantity_factor_snapshot"] == "12.00000000"
    assert first["base_quantity"] == "24.0000" and first["inventory_unit_cost"] == "10000.0000"
    assert first["presentation_code_snapshot"] == "CAJA12" and first["unit_code_snapshot"] == "UND"
    assert first["supplier_lead_time_snapshot_hours"] == "48.50"
    assert second["subtotal"] == "15001.50" and second["total"] == "15000.00"
    assert second["presentation_code_snapshot"] == "UND" and second["base_quantity_factor_snapshot"] == "1.00000000"
    assert third["base_quantity"] == "1.5000"
    # Spec 021: impuesto por tasa (arroz 19 %, aceite 0 %): 45.600 + 0 + 3.000 × 19 % = 46.170.
    assert third["tax_amount"] == "570.00" and second["tax_amount"] == "0.00"
    assert purchase["subtotal"] == "258001.50"
    assert purchase["discount_total"] == "1.50"
    assert purchase["tax_total"] == "46170.00"
    assert purchase["total"] == "304170.00"


def test_draft_without_lines_is_allowed(buyer, world) -> None:
    response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world))
    assert response.status_code == 201
    assert response.json()["lines"] == [] and response.json()["total"] == "0.00"


def test_cash_condition_keeps_due_date_on_operation_date(buyer, world) -> None:
    """Spec 020 (FR-020-08): la única condición admitida es de contado."""
    response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, supplier_payment_condition_id=world.condition))
    purchase = response.json()
    assert response.status_code == 201, response.text
    assert purchase["payment_condition_code_snapshot"] == "CASH" and purchase["payment_terms_days_snapshot"] == 0
    assert purchase["due_date"] == purchase["operation_date"]


def test_operation_date_in_future_is_422(buyer, world, clock) -> None:
    clock.fixed = datetime(2026, 10, 6, 23, 30, tzinfo=UTC)  # 18:30 en Bogotá: "hoy" es el 6
    response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, operation_date="2026-10-07"))
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "OPERATION_DATE_IN_FUTURE"
    assert buyer.post(f"{base(world)}/purchases", json=purchase_body(world, operation_date="2026-10-06")).status_code == 201


def test_lines_limit(buyer, world, fakes) -> None:
    lines = distinct_lines(fakes, world.product, 101)  # spec 021: una presentación por línea
    response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, *lines))
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "LINES_LIMIT_EXCEEDED"
    assert buyer.post(f"{base(world)}/purchases", json=purchase_body(world, *lines[:100])).status_code == 201


def test_add_line_101_is_422(buyer, world, fakes) -> None:
    lines = distinct_lines(fakes, world.product, 101)
    created = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, *lines[:100])).json()
    response = buyer.post(
        f"{base(world)}/purchases/{created['id']}/details", json={**lines[100], "version": created["version"]}
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "LINES_LIMIT_EXCEEDED"


def test_unknown_fields_and_totals_are_rejected(buyer, world) -> None:
    for extra in ({"total": "1"}, {"status": "CONFIRMED"}, {"supplier_name_snapshot": "x"}):
        response = buyer.post(f"{base(world)}/purchases", json={**purchase_body(world), **extra})
        assert response.status_code == 422
        assert response.json()["errors"][0]["code"] == "UNKNOWN_FIELD"
    response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, {**line(world.product), "subtotal": "1"}))
    assert response.status_code == 422


def test_amount_validation(buyer, world) -> None:
    cases = [
        (line(world.product, quantity="0"), "QUANTITY_NOT_POSITIVE"),
        (line(world.product, quantity="1.00001"), "TOO_MANY_DECIMALS"),
        (line(world.product, unit_cost="-1"), "UNIT_COST_NOT_POSITIVE"),
        (line(world.product, unit_cost="0"), "UNIT_COST_NOT_POSITIVE"),
        (line(world.product, unit_cost="10", discount_amount="20.01", quantity="2"), "DISCOUNT_EXCEEDS_SUBTOTAL"),
        (line(world.product, unit_cost="10", discount_amount="20", quantity="2"), "NET_COST_NOT_POSITIVE"),
        (line(world.product, quantity="0.0001", company_product_presentation_id=world.presentation), None),
    ]
    for item, code in cases:
        response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, item))
        if code is None:
            assert response.status_code == 201, response.text
        else:
            assert response.status_code == 422, response.text
            assert response.json()["errors"][0]["code"] == code
            assert response.json()["errors"][0]["field"].startswith("lines[0].")


def test_base_quantity_precision(buyer, world, fakes) -> None:
    from decimal import Decimal

    from purchase_service.application.ports import GlobalPresentationInfo

    fakes.catalog.presentations[world.global_presentation] = GlobalPresentationInfo(world.global_presentation, "MEDIA", "Media", Decimal("0.5"))
    response = buyer.post(
        f"{base(world)}/purchases",
        json=purchase_body(world, line(world.product, quantity="1.0001", company_product_presentation_id=world.presentation)),
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "BASE_QUANTITY_PRECISION"


def test_dependency_unavailable_persists_nothing(buyer, world, fakes, test_engine) -> None:
    from tests.conftest import count_rows

    for availability in (fakes.cr.availability, fakes.catalog.availability, fakes.party.availability, fakes.oc.availability):
        availability.down = True
        response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, line(world.product)))
        assert response.status_code == 503, response.text
        assert response.json()["dependency"] == availability.provider
        availability.down = False
    fakes.pr.availability.down = True
    response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, supplier_payment_condition_id=world.condition))
    assert response.status_code == 503 and response.json()["dependency"] == "payment-reference"
    fakes.oc.access_down = True
    assert buyer.post(f"{base(world)}/purchases", json=purchase_body(world)).json()["dependency"] == "operational-context"
    assert count_rows(test_engine, "purchases") == 0
    assert count_rows(test_engine, "audit_outbox") == 0


def test_creation_is_audited(buyer, world, test_engine) -> None:
    from tests.conftest import fetch

    created = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, line(world.product))).json()
    rows = fetch(test_engine, "SELECT payload FROM audit_outbox")
    assert len(rows) == 1
    payload = rows[0]["payload"]
    assert payload["action"] == "CREATE_PURCHASE" and payload["entity_id"] == created["id"]
    assert payload["result"] == "SUCCESS"
