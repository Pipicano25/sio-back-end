"""Confirmación (Historia 2; FR-014 a FR-020, DS-02, P-05, R-12; RC-03; T050)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from tests.conftest import base, count_rows, fetch, line, new_key, sale_body, user_sub

PROFITABILITY = ("unit_cost_snapshot", "cost_total", "cost_known", "gross_margin_amount", "gross_margin_percentage")


def test_confirmation_applies_output_copies_fifo_cost_and_assigns_number(
    seller, supervisor, world, fakes, clock, make_sequence, make_draft, confirm
) -> None:
    clock.fixed = datetime(2026, 10, 7, 15, 0, tzinfo=UTC)
    make_sequence(reset_policy="MONTHLY")
    draft = make_draft(
        line(world.product, "2", company_product_presentation_id=world.presentation, price_list_id=world.price_list,
             tax_amount="5700"),
        line(world.product_2, "3", discount_amount="300"),
    )
    response = confirm(draft)
    assert response.status_code == 200, response.text
    sale = response.json()
    assert sale["status"] == "CONFIRMED"
    assert sale["number"] == "FV-202610-000001" and sale["sequence_value"] == 1
    assert sale["sale_sequence_id"] is not None and sale["pending_operation_id"] is None
    assert (sale["operation_date"], sale["due_date"], sale["payment_condition_code_snapshot"]) == (
        "2026-10-07", "2026-10-07", "CASH",
    )
    # El vendedor no ve la rentabilidad ni siquiera en la respuesta de la confirmación.
    assert "has_unknown_cost" not in sale and not any(name in sale["lines"][0] for name in PROFITABILITY)

    [output] = fakes.inventory.outputs()
    assert sale["inventory_operation_id"] == str(output.ref.id)
    payload = output.payload
    assert payload["origin_type"] == "SALE" and payload["origin_id"] == draft["id"]
    assert payload["company_id"] == str(world.company) and payload["branch_id"] == str(world.branch)
    assert payload["application_user_id"] == str(fakes.oc.members[(user_sub("ventas.test"), world.company)])
    assert payload["reason"] is None
    first, second = payload["lines"]
    # Cantidad en unidad base y sin costo: Inventory calcula el FIFO (RN-05, RN-06).
    assert first == {
        "origin_detail_id": draft["lines"][0]["id"],
        "company_product_id": str(world.product),
        "quantity": "24.0000",
    }
    assert second["quantity"] == "3.0000" and "unit_cost" not in second
    assert fakes.inventory.balance(world.branch, world.product) == 1000 - 24

    seen = supervisor.get(f"{base(world)}/sales/{draft['id']}").json()
    box, oil = seen["lines"]
    # P-05: costo por unidad base exactamente como lo informa Inventory; costo total = valor del movimiento.
    assert (box["unit_cost_snapshot"], box["cost_total"], box["cost_known"]) == ("1000.0000", "24000.00", True)
    assert (box["gross_margin_amount"], box["gross_margin_percentage"]) == ("8000.00", "25.0000")
    assert (oil["unit_cost_snapshot"], oil["cost_total"]) == ("6000.0000", "18000.00")
    # neto = 27000 − 300 = 26700; margen = 8700; 8700 / 26700 × 100 = 32.5843 (impuestos excluidos)
    assert (oil["gross_margin_amount"], oil["gross_margin_percentage"]) == ("8700.00", "32.5843")
    assert seen["has_unknown_cost"] is False


def test_operation_key_is_the_operation_id(seller, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    key = new_key()
    confirm(draft, key)
    [operation] = fetch(test_engine, "SELECT * FROM sale_operations")
    [output] = fakes.inventory.outputs()
    assert output.payload["operation_key"] == str(operation["id"])
    assert output.payload["correlation_id"] == str(operation["correlation_id"])
    assert operation["status"] == "SUCCEEDED" and operation["idempotency_key"] == key
    assert operation["inventory_operation_id"] == output.ref.id
    assert operation["created_by"] == user_sub("ventas.test") and operation["completed_at"] is not None
    assert operation["application_user_id"] == fakes.oc.members[(user_sub("ventas.test"), world.company)]


def test_correlation_id_is_propagated(seller, world, fakes, make_sequence, make_draft) -> None:
    make_sequence()
    draft = make_draft()
    correlation = "7d0c2e7a-6b38-4c0b-9e8b-2f1c0b6c9a11"
    seller.post(
        f"{base(world)}/sales/{draft['id']}/confirmation",
        json={"version": 1},
        headers={"Idempotency-Key": new_key(), "X-Correlation-Id": correlation},
    )
    assert fakes.inventory.outputs()[0].payload["correlation_id"] == correlation


def test_business_date_is_the_confirmation_day(seller, world, fakes, clock, make_sequence, make_draft, confirm) -> None:
    """R-12: un borrador de octubre confirmado en noviembre toma la fecha y el período de noviembre."""
    make_sequence(reset_policy="MONTHLY")
    clock.fixed = datetime(2026, 10, 31, 20, 0, tzinfo=UTC)  # 15:00 del 31 de octubre en Bogotá
    draft = make_draft()
    assert draft["operation_date"] == "2026-10-31"
    clock.fixed = datetime(2026, 11, 1, 5, 30, tzinfo=UTC)  # 00:30 del 1 de noviembre en Bogotá
    confirmed = confirm(draft).json()
    assert (confirmed["operation_date"], confirmed["due_date"]) == ("2026-11-01", "2026-11-01")
    assert confirmed["number"] == "FV-202611-000001"


def test_snapshots_are_refreshed_and_frozen(seller, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    fakes.cr.customers[world.customer] = replace(fakes.cr.customers[world.customer], display_name="Ana Renombrada")
    fakes.cr.products[world.product] = replace(fakes.cr.products[world.product], display_name="Arroz renombrado")
    confirmed = confirm(draft).json()
    assert confirmed["customer_name_snapshot"] == "Ana Renombrada"
    assert confirmed["lines"][0]["product_name_snapshot"] == "Arroz renombrado"
    fakes.cr.customers[world.customer] = replace(fakes.cr.customers[world.customer], display_name="Otro nombre")
    again = seller.get(f"{base(world)}/sales/{draft['id']}").json()
    assert again["customer_name_snapshot"] == "Ana Renombrada"  # congelado (DS-02)


def test_requires_key_lines_and_version(seller, world, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    empty = seller.post(f"{base(world)}/sales", json=sale_body(world)).json()
    response = seller.post(f"{base(world)}/sales/{empty['id']}/confirmation", json={"version": 1})
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    response = confirm(empty)
    assert response.status_code == 422 and response.json()["code"] == "SALES.SALE_WITHOUT_LINES"
    draft = make_draft()
    response = confirm(draft, version=7)
    assert response.status_code == 409 and response.json()["code"] == "SALES.VERSION_CONFLICT"


def test_reference_no_longer_fit_rejects_without_effects(seller, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft(line(world.product), line(world.product_2))
    fakes.cr.products[world.product_2] = replace(fakes.cr.products[world.product_2], status="INACTIVE")
    response = confirm(draft)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "SALES.REFERENCES_NOT_ELIGIBLE"
    assert body["errors"][0]["code"] == "PRODUCT_INACTIVE" and body["errors"][0]["line_number"] == 2
    assert fakes.inventory.outputs() == []
    assert count_rows(test_engine, "sale_operations") == 0
    assert seller.get(f"{base(world)}/sales/{draft['id']}").json()["status"] == "DRAFT"


def test_without_sequence_rejects_before_inventory(world, fakes, make_draft, confirm, test_engine) -> None:
    draft = make_draft()
    response = confirm(draft)
    assert response.status_code == 409 and response.json()["code"] == "SALES.SEQUENCE_NOT_CONFIGURED"
    assert count_rows(test_engine, "sale_operations") == 0
    assert fakes.inventory.outputs() == []


def test_exhausted_sequence_rejects_before_inventory(world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence(maximum_number=1)
    assert confirm(make_draft()).status_code == 200
    response = confirm(make_draft())
    assert response.status_code == 409 and response.json()["code"] == "SALES.SEQUENCE_EXHAUSTED"
    assert len(fakes.inventory.outputs()) == 1


def test_definitive_inventory_rejection_fails_operation(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    fakes.inventory.reject_output = (422, "VALIDATION_ERROR")
    response = confirm(draft)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "SALES.INVENTORY_REJECTED" and body["details"]["inventory_code"] == "VALIDATION_ERROR"
    [operation] = fetch(test_engine, "SELECT status, error_code FROM sale_operations")
    assert operation == {"status": "FAILED", "error_code": "INVENTORY_REJECTED"}
    sale = fetch(test_engine, "SELECT status, number FROM sales")[0]
    assert sale == {"status": "DRAFT", "number": None}
    assert count_rows(test_engine, "sale_sequence_counters") == 0  # no consume número


def test_inactive_operator_is_409(as_user, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    user = fakes.oc.members[(user_sub("ventas.test"), world.company)]
    fakes.oc.users[user] = replace(fakes.oc.users[user], status="INACTIVE")
    response = confirm(draft)
    assert response.status_code == 409
    assert response.json()["errors"][0]["code"] == "APPLICATION_USER_INACTIVE"


def test_confirmation_requires_branch_assignment(as_user, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft()
    fakes.oc.assignments.discard((user_sub("ventas.test"), world.branch))
    response = confirm(draft)
    assert response.status_code == 403 and response.json()["code"] == "SALES.BRANCH_ACCESS_DENIED"


def test_confirmation_is_audited_without_costs(world, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    confirmed = confirm(draft).json()
    events = [row["payload"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox ORDER BY created_at")]
    confirm_event = [event for event in events if event["action"] == "CONFIRM_SALE"]
    assert len(confirm_event) == 1
    assert confirm_event[0]["result"] == "SUCCESS"
    assert confirm_event[0]["new_values"]["number"] == confirmed["number"]
    assert confirm_event[0]["new_values"]["inventory_operation_id"] == confirmed["inventory_operation_id"]
    assert not any(word in str(confirm_event[0]) for word in ("cost", "margin"))
