"""Venta en borrador (Historia 1; FR-001 a FR-012, DS-11, DP-01, RN-01; T031)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.conftest import base, line, sale_body, user_sub

PROFITABILITY = ("unit_cost_snapshot", "cost_total", "cost_known", "gross_margin_amount", "gross_margin_percentage")


def test_create_draft_with_resolved_prices(seller, world, fakes, clock) -> None:
    clock.fixed = datetime(2026, 10, 7, 23, 30, tzinfo=UTC)  # 18:30 en Bogotá: la fecha de negocio es el 7
    fakes.inventory.availability.fail_if_called = True  # RN-01: el borrador nunca toca Inventory
    body = sale_body(
        world,
        line(world.product, "2", company_product_presentation_id=world.presentation, price_list_id=world.price_list),
        line(world.product_2, "3"),
        line(world.product, "1.5"),
        observations="Venta de mostrador (ficticia)",
    )
    response = seller.post(f"{base(world)}/sales", json=body)
    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["status"] == "DRAFT" and sale["number"] is None and sale["inventory_operation_id"] is None
    assert sale["version"] == 1 and sale["currency_code"] == "COP"
    assert sale["created_by"] == user_sub("ventas.test")
    assert sale["created_by_user_id"] == str(fakes.oc.members[(user_sub("ventas.test"), world.company)])
    # DP-01: solo contado; fecha de negocio = hoy en la zona de la sucursal (R-12).
    assert sale["customer_payment_condition_id"] is None
    assert (sale["payment_condition_code_snapshot"], sale["payment_terms_days_snapshot"]) == ("CASH", 0)
    assert sale["operation_date"] == "2026-10-07" and sale["due_date"] == "2026-10-07"
    assert sale["customer_name_snapshot"] == "Ana Ficticia Pérez"
    assert sale["customer_identification_snapshot"] == "CC 1020304050"
    assert (sale["payment_method_code_snapshot"], sale["payment_method_name_snapshot"]) == ("CASH", "Efectivo")
    assert [item["line_number"] for item in sale["lines"]] == [1, 2, 3]

    box, oil, rice = sale["lines"]
    # Lista pedida con precio por presentación: se usa tal cual.
    assert box["unit_price"] == "16000.0000" and box["price_source"] == "PRICE_LIST_ITEM"
    assert box["price_list_id"] == str(world.price_list) and box["price_list_item_id"] == str(world.item_box)
    assert box["price_list_requested"] is True
    # Spec 021 (B-4): el precio de la lista es el importe final; Sales no suma impuesto.
    assert (box["subtotal"], box["tax_amount"], box["total"]) == ("32000.00", "0.00", "32000.00")
    assert box["base_quantity_factor_snapshot"] == "12.00000000" and box["base_quantity"] == "24.0000"
    assert box["presentation_code_snapshot"] == "CAJA12" and box["unit_code_snapshot"] == "UND"
    # Sin lista: precio explícito de su presentación unidad en la lista predeterminada (spec 019).
    assert oil["unit_price"] == "9000.0000" and oil["price_source"] == "PRICE_LIST_ITEM"
    assert oil["price_list_id"] == str(world.default_list) and oil["price_list_item_id"] == str(world.item_unit_2)
    assert oil["price_list_requested"] is False and oil["base_quantity_factor_snapshot"] == "1.00000000"
    assert oil["subtotal"] == "27000.00" and oil["discount_amount"] == "0.00" and oil["total"] == "27000.00"
    assert rice["unit_price"] == "1500.0000" and rice["subtotal"] == "2250.00" and rice["base_quantity"] == "1.5000"
    assert (sale["subtotal"], sale["discount_total"], sale["tax_total"], sale["total"]) == (
        "61250.00", "0.00", "0.00", "61250.00",
    )
    # ventas.test no tiene read-profitability: los campos se omiten (no se envían como null).
    assert "has_unknown_cost" not in sale
    assert not any(name in item for item in sale["lines"] for name in PROFITABILITY)


def test_supervisor_sees_profitability_fields_empty_in_draft(supervisor, world, fakes) -> None:
    fakes.oc.add_member(user_sub("supervisor.test"), world.company, branches=(world.branch,))
    response = supervisor.post(f"{base(world)}/sales", json=sale_body(world, line(world.product)))
    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["has_unknown_cost"] is False
    assert all(sale["lines"][0][name] is None for name in PROFITABILITY)


def test_organization_customer(seller, world) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, company_customer_id=world.customer_org))
    assert response.status_code == 201, response.text
    assert response.json()["customer_identification_snapshot"] == "NIT 900123456"


def test_draft_without_lines_is_allowed(seller, world) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world))
    assert response.status_code == 201
    assert response.json()["lines"] == [] and response.json()["total"] == "0.00"


@pytest.mark.parametrize(
    ("extra", "code", "field"),
    [
        ({"operation_date": "2026-10-07"}, "OPERATION_DATE_NOT_ALLOWED", "operation_date"),
        ({"customer_payment_condition_id": "5f3c0a8e-3a0f-4b1e-8f1a-111111111111"}, "PAYMENT_CONDITION_NOT_ALLOWED",
         "customer_payment_condition_id"),
        ({"payment_condition_code_snapshot": "CREDIT"}, "PAYMENT_CONDITION_NOT_ALLOWED", "payment_condition_code_snapshot"),
        ({"due_date": "2026-11-07"}, "PAYMENT_CONDITION_NOT_ALLOWED", "due_date"),
    ],
)
def test_date_and_payment_condition_are_not_accepted(seller, world, extra, code, field) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, **extra))
    assert response.status_code == 422
    assert {(error["code"], error["field"]) for error in response.json()["errors"]} == {(code, field)}


def test_manual_price_is_rejected(seller, world) -> None:
    """DS-11: sin precio manual."""
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product, unit_price="1")))
    assert response.status_code == 422
    assert response.json()["errors"][0] == {
        "field": "lines[0].unit_price",
        "message": "El precio lo resuelve el sistema; no se admite precio manual.",
        "code": "UNIT_PRICE_NOT_ALLOWED",
    }


@pytest.mark.parametrize("field", ["subtotal", "total", "unit_cost_snapshot", "cost_total", "gross_margin_amount"])
def test_amounts_and_costs_are_not_accepted(seller, world, field) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product, **{field: "1"})))
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "UNKNOWN_FIELD"


def test_lines_limit(seller, world) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, *[line(world.product)] * 101))
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "LINES_LIMIT_EXCEEDED"
    assert seller.post(f"{base(world)}/sales", json=sale_body(world, *[line(world.product)] * 100)).status_code == 201


def test_add_line_101_is_422(seller, world) -> None:
    created = seller.post(f"{base(world)}/sales", json=sale_body(world, *[line(world.product)] * 100)).json()
    response = seller.post(
        f"{base(world)}/sales/{created['id']}/details", json={**line(world.product), "version": created["version"]}
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "LINES_LIMIT_EXCEEDED"


@pytest.mark.parametrize(
    ("quantity", "discount", "code"),
    [
        ("0", "0", "QUANTITY_NOT_POSITIVE"),
        ("1.00001", "0", "TOO_MANY_DECIMALS"),
        ("1", "1500.01", "DISCOUNT_NOT_ALLOWED"),  # spec 020: sin descuentos
        ("1", "0.01", "DISCOUNT_NOT_ALLOWED"),
    ],
)
def test_line_amount_rules(seller, world, quantity, discount, code) -> None:
    response = seller.post(
        f"{base(world)}/sales", json=sale_body(world, line(world.product, quantity, discount_amount=discount))
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == code


def test_base_quantity_precision(seller, world, fakes) -> None:
    from decimal import Decimal

    fakes.catalog.presentations[world.global_presentation] = fakes.catalog.presentations[
        world.global_presentation
    ].__class__(world.global_presentation, "MEDIA", "Media unidad", Decimal("0.5"))
    response = seller.post(
        f"{base(world)}/sales",
        json=sale_body(world, line(world.product, "1.0001", company_product_presentation_id=world.presentation)),
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "BASE_QUANTITY_PRECISION"


def test_dependency_unavailable_is_503_without_effects(seller, world, fakes, test_engine) -> None:
    from tests.conftest import count_rows

    fakes.cr.availability.down = True
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product)))
    assert response.status_code == 503
    assert response.json()["dependency"] == "commercial-relationship"
    assert count_rows(test_engine, "sales") == 0
