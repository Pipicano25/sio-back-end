"""Precio de la línea en el borrador (FR-006, DS-01, DS-04, P-02, P-03, P-04; research.md R-07; T032)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.conftest import base, count_rows, line, sale_body


def post(seller, world, *lines):
    return seller.post(f"{base(world)}/sales", json=sale_body(world, *lines))


def test_base_unit_price_with_presentation_is_converted_to_four_decimals(seller, world, fakes) -> None:
    """P-04: `sale_price` por unidad base × factor, redondeado a 4 decimales (nunca a 2)."""
    fakes.cr.sale_prices[world.product] = (Decimal("1234.5678"), "COP")
    fakes.catalog.presentations[world.global_presentation] = fakes.catalog.presentations[
        world.global_presentation
    ].__class__(world.global_presentation, "OCTAVO", "Octavo", Decimal("0.125"))
    response = post(seller, world, line(world.product, "8", company_product_presentation_id=world.presentation))
    assert response.status_code == 201, response.text
    detail = response.json()["lines"][0]
    assert detail["unit_price"] == "154.3210"  # 154.320975 → 154.3210
    assert detail["subtotal"] == "1234.57"  # 8 × 154.3210 = 1234.568 → 1234.57


def test_list_price_for_the_whole_product_is_converted_with_the_factor(seller, world, fakes) -> None:
    fakes.cr.set_price(world.price_list, world.product, None, "1300.00")
    response = post(
        seller,
        world,
        line(world.product, "1", company_product_presentation_id=world.presentation, price_list_id=world.price_list_2),
    )
    assert response.status_code == 409  # la lista 2 no tiene precio para el producto
    fakes.cr.default_list = world.price_list
    response = post(seller, world, line(world.product, "1", company_product_presentation_id=world.presentation))
    assert response.status_code == 201, response.text
    detail = response.json()["lines"][0]
    # Lista predeterminada: el ítem de la presentación (16000) tiene prioridad sobre el general del producto.
    assert (detail["unit_price"], detail["price_list_id"], detail["price_list_requested"]) == (
        "16000.0000", str(world.price_list), False,
    )


def test_default_list_is_recorded_without_the_requested_flag(seller, world, fakes) -> None:
    fakes.cr.default_list = world.price_list
    response = post(seller, world, line(world.product_2, "2"))
    assert response.status_code == 201, response.text
    detail = response.json()["lines"][0]
    assert detail["price_list_id"] == str(world.price_list) and detail["price_list_item_id"] == str(world.item_product_2)
    assert detail["price_list_requested"] is False and detail["unit_price"] == "8500.0000"


@pytest.mark.parametrize(
    ("setup", "price_list", "status", "code"),
    [
        (lambda f, w: f.cr.sale_prices.__setitem__(w.product, (None, "COP")), None, 409, "PRICE_NOT_AVAILABLE"),
        (lambda f, w: None, "price_list_2", 409, "PRICE_NOT_IN_LIST"),
        (lambda f, w: f.cr.list_applicable.__setitem__(w.price_list, False), "price_list", 409, "PRICE_LIST_NOT_APPLICABLE"),
        (lambda f, w: f.cr.sale_prices.__setitem__(w.product, (Decimal("5"), "USD")), None, 409, "PRICE_CURRENCY_MISMATCH"),
    ],
)
def test_price_rejections(seller, world, fakes, test_engine, setup, price_list, status, code) -> None:
    setup(fakes, world)
    extra = {"price_list_id": getattr(world, price_list)} if price_list else {}
    response = post(seller, world, line(world.product, "1", **extra))
    assert response.status_code == status, response.text
    assert response.json()["code"] == "SALES.REFERENCES_NOT_ELIGIBLE"
    assert response.json()["errors"][0]["code"] == code
    assert count_rows(test_engine, "sales") == 0


def test_inactive_list_is_409_and_unknown_list_is_422(seller, world, fakes) -> None:
    """P-03: Commercial Relationship responde PRICE_LIST_NOT_APPLICABLE en ambos casos; Sales consulta la lista."""
    fakes.cr.price_lists[world.price_list] = fakes.cr.price_lists[world.price_list].__class__(
        world.price_list, world.company, "INACTIVE"
    )
    inactive = post(seller, world, line(world.product, "1", price_list_id=world.price_list))
    assert inactive.status_code == 409 and inactive.json()["errors"][0]["code"] == "PRICE_LIST_NOT_APPLICABLE"

    from uuid import uuid4

    unknown = post(seller, world, line(world.product, "1", price_list_id=uuid4()))
    assert unknown.status_code == 422 and unknown.json()["errors"][0]["code"] == "PRICE_LIST_NOT_FOUND"

    foreign = uuid4()
    fakes.cr.price_lists[foreign] = fakes.cr.price_lists[world.price_list].__class__(foreign, world.other_company, "ACTIVE")
    other_company = post(seller, world, line(world.product, "1", price_list_id=foreign))
    assert other_company.status_code == 422 and other_company.json()["errors"][0]["code"] == "PRICE_LIST_NOT_FOUND"


def test_list_lookup_unavailable_is_503(seller, world, fakes) -> None:
    """P-03: si la consulta de la lista no está disponible → `503 commercial-relationship`."""
    fakes.cr.list_applicable[world.price_list] = False
    original = fakes.cr.get_price_list

    def down(price_list_id):
        from sales_service.application.exceptions import DependencyUnavailableError

        raise DependencyUnavailableError("commercial-relationship", operation="price_list", cause="prueba")

    fakes.cr.get_price_list = down
    try:
        response = post(seller, world, line(world.product, "1", price_list_id=world.price_list))
    finally:
        fakes.cr.get_price_list = original
    assert response.status_code == 503 and response.json()["dependency"] == "commercial-relationship"


def test_all_lines_are_priced_in_a_single_call(seller, world, fakes) -> None:
    response = post(seller, world, *[line(world.product, "1")] * 30, line(world.product_2, "1"))
    assert response.status_code == 201
    calls = [call for call in fakes.cr.availability.calls if call[0] == "applicable_prices"]
    assert len(calls) == 1 and len(calls[0][1]) == 31
