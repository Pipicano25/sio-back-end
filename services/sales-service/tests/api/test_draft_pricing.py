"""Precio de la línea en el borrador (FR-006, DS-01, DS-04, P-02, P-03, P-04; spec 019; research.md R-07; T032)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.conftest import base, count_rows, line, sale_body


def post(seller, world, *lines):
    return seller.post(f"{base(world)}/sales", json=sale_body(world, *lines))


def test_presentation_price_is_used_as_is_without_the_factor(seller, world, fakes) -> None:
    """Spec 019: el precio explícito de la presentación se usa tal cual; el factor solo convierte la cantidad."""
    fakes.cr.set_price(world.default_list, world.product, world.presentation, "1234.5678")
    fakes.catalog.presentations[world.global_presentation] = fakes.catalog.presentations[
        world.global_presentation
    ].__class__(world.global_presentation, "OCTAVO", "Octavo", Decimal("0.125"))
    response = post(seller, world, line(world.product, "8", company_product_presentation_id=world.presentation))
    assert response.status_code == 201, response.text
    detail = response.json()["lines"][0]
    assert detail["unit_price"] == "1234.5678" and detail["price_source"] == "PRICE_LIST_ITEM"
    assert detail["subtotal"] == "9876.54"  # 8 × 1234.5678 = 9876.5424
    assert detail["base_quantity_factor_snapshot"].startswith("0.125")


def test_no_general_price_and_no_conversion_between_presentations(seller, world, fakes) -> None:
    """Spec 019: el precio de la unidad nunca se convierte en el de la caja (ni al revés)."""
    fakes.cr.set_price(world.price_list, world.product, world.unit_presentation, "1300.00")
    response = post(
        seller,
        world,
        line(world.product, "1", company_product_presentation_id=world.presentation, price_list_id=world.price_list_2),
    )
    assert response.status_code == 409  # la lista 2 no tiene precio para la caja
    fakes.cr.default_list = world.price_list
    response = post(seller, world, line(world.product, "1", company_product_presentation_id=world.presentation))
    assert response.status_code == 201, response.text
    detail = response.json()["lines"][0]
    assert (detail["unit_price"], detail["price_list_id"], detail["price_list_requested"]) == (
        "16000.0000", str(world.price_list), False,
    )
    del fakes.cr.items[(world.price_list, world.product, world.presentation)]  # la caja se queda sin precio
    response = post(seller, world, line(world.product, "1", company_product_presentation_id=world.presentation))
    assert response.status_code == 409, response.text  # no se usa 1300 × 12
    assert response.json()["errors"][0]["code"] == "PRICE_NOT_IN_LIST"


def test_line_without_presentation_is_rejected(seller, world, fakes, test_engine) -> None:
    """Spec 019: toda línea indica su presentación, también para vender la unidad base."""
    response = post(seller, world, line(world.product, "1", company_product_presentation_id=None))
    assert response.status_code == 422, response.text
    assert "company_product_presentation_id" in response.text
    assert count_rows(test_engine, "sales") == 0


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
        (lambda f, w: f.cr.set_unit_price(w.product, None), None, 409, "PRICE_NOT_IN_LIST"),
        (lambda f, w: setattr(f.cr, "default_list", None), None, 409, "PRICE_NOT_AVAILABLE"),
        (lambda f, w: None, "price_list_2", 409, "PRICE_NOT_IN_LIST"),
        (lambda f, w: f.cr.list_applicable.__setitem__(w.price_list, False), "price_list", 409, "PRICE_LIST_NOT_APPLICABLE"),
        (lambda f, w: f.cr.set_unit_price(w.product, "5", "USD"), None, 409, "PRICE_CURRENCY_MISMATCH"),
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


@pytest.mark.parametrize(("resolution", "basis"), [("COMPANY_PRODUCT_SALE_PRICE", "BASE_UNIT"), ("PRICE_LIST_ITEM", "BASE_UNIT")])
def test_fallback_or_base_unit_price_from_an_old_version_is_never_used(seller, world, fakes, test_engine, resolution, basis) -> None:
    """Spec 019: un respaldo o un precio por unidad base es una dependencia incompatible (`503`), nunca un precio."""
    original = fakes.cr.resolve_prices

    def legacy(company_id, lines, at):
        result = original(company_id, lines, at)
        return {key: price.__class__(price.line_id, True, resolution, basis, Decimal("1500.00"), "COP", None, None)
                for key, price in result.items()}

    fakes.cr.resolve_prices = legacy
    response = post(seller, world, line(world.product, "1"))
    assert response.status_code == 503, response.text
    assert count_rows(test_engine, "sales") == 0
