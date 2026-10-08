"""Precio cambiado al confirmar (DS-05, P-02, FR-015; research.md R-07; T051).

La confirmación repite la resolución con la intención original de cada línea; si el precio,
la lista o el ítem difieren de lo guardado → `409 PRICES_CHANGED`, sin salida, sin número, sin
operación y sin modificar el borrador.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from tests.conftest import base, count_rows, fetch, line


def assert_no_effects(fakes, test_engine, draft) -> None:
    assert fakes.inventory.outputs() == []
    assert count_rows(test_engine, "sale_operations") == 0
    assert count_rows(test_engine, "sale_sequence_counters") == 0
    row = fetch(test_engine, "SELECT status, number, version FROM sales")[0]
    assert row == {"status": "DRAFT", "number": None, "version": draft["version"]}


def test_list_price_changed(seller, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft(
        line(world.product_2, "1"),
        line(world.product, "1", company_product_presentation_id=world.presentation, price_list_id=world.price_list),
    )
    fakes.cr.items[(world.price_list, world.product, world.presentation)].unit_price = Decimal("16500.00")
    response = confirm(draft)
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "SALES.PRICES_CHANGED"
    [change] = body["errors"]
    assert change["code"] == "PRICE_CHANGED" and change["line_number"] == 2 and change["field"] == "lines[1].unit_price"
    assert change["stored"] == {
        "unit_price": "16000.0000", "price_list_id": str(world.price_list), "price_list_item_id": str(world.item_box),
    }
    assert change["current"]["unit_price"] == "16500.0000"
    assert_no_effects(fakes, test_engine, draft)


def test_item_replaced_with_the_same_price_is_a_change(seller, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft(line(world.product_2, "1", price_list_id=world.price_list))
    new_item = fakes.cr.set_price(world.price_list, world.product_2, None, "8500.00")
    response = confirm(draft)
    assert response.status_code == 409 and response.json()["code"] == "SALES.PRICES_CHANGED"
    change = response.json()["errors"][0]
    assert change["current"]["price_list_item_id"] == str(new_item) and change["current"]["unit_price"] == "8500.0000"
    assert_no_effects(fakes, test_engine, draft)


def test_default_list_changed_without_explicit_request(seller, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    """P-02: sin lista pedida, la confirmación vuelve a pedir la predeterminada y detecta el cambio."""
    make_sequence()
    draft = make_draft(line(world.product_2, "1"))  # sale_price 9000, sin lista
    fakes.cr.default_list = world.price_list  # ahora la predeterminada tiene 8500
    response = confirm(draft)
    assert response.status_code == 409 and response.json()["code"] == "SALES.PRICES_CHANGED"
    change = response.json()["errors"][0]
    assert change["stored"]["price_list_id"] is None and change["current"]["price_list_id"] == str(world.price_list)
    assert_no_effects(fakes, test_engine, draft)


def test_explicit_list_is_kept_when_the_default_changes(seller, world, fakes, make_sequence, make_draft, confirm) -> None:
    """P-02: con lista pedida, cambiar la predeterminada no afecta la línea (misma intención)."""
    make_sequence()
    draft = make_draft(line(world.product_2, "1", price_list_id=world.price_list))
    fakes.cr.set_price(world.price_list_2, world.product_2, None, "7000.00")
    fakes.cr.default_list = world.price_list_2
    response = confirm(draft)
    assert response.status_code == 200, response.text
    assert response.json()["lines"][0]["unit_price"] == "8500.0000"


def test_simple_price_changed(seller, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft(line(world.product, "2"))
    fakes.cr.sale_prices[world.product] = (Decimal("1550.00"), "COP")
    response = confirm(draft)
    assert response.status_code == 409
    change = response.json()["errors"][0]
    assert (change["stored"]["unit_price"], change["current"]["unit_price"]) == ("1500.0000", "1550.0000")
    assert_no_effects(fakes, test_engine, draft)


def test_explicit_list_inactivated_is_not_applicable(seller, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft(line(world.product_2, "1", price_list_id=world.price_list))
    fakes.cr.price_lists[world.price_list] = replace(fakes.cr.price_lists[world.price_list], status="INACTIVE")
    response = confirm(draft)
    assert response.status_code == 409
    assert response.json()["code"] == "SALES.REFERENCES_NOT_ELIGIBLE"
    assert response.json()["errors"][0]["code"] == "PRICE_LIST_NOT_APPLICABLE"
    assert_no_effects(fakes, test_engine, draft)


def test_updating_the_line_then_confirming_uses_the_current_price(seller, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft(line(world.product, "2"))
    fakes.cr.sale_prices[world.product] = (Decimal("1550.00"), "COP")
    assert confirm(draft).status_code == 409
    detail = draft["lines"][0]
    updated = seller.put(
        f"{base(world)}/sales/{draft['id']}/details/{detail['id']}", json={**line(world.product, "2"), "version": 1}
    ).json()
    confirmed = confirm(updated)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["lines"][0]["unit_price"] == "1550.0000" and confirmed.json()["total"] == "3100.00"
    # Una vez confirmada, el precio no cambia aunque cambie el catálogo (RN-04).
    fakes.cr.sale_prices[world.product] = (Decimal("9999.00"), "COP")
    assert seller.get(f"{base(world)}/sales/{draft['id']}").json()["lines"][0]["unit_price"] == "1550.0000"


@pytest.mark.parametrize("dependency", ["cr", "party", "catalog"])
def test_revalidation_dependency_down_is_503_without_effects(seller, world, fakes, make_sequence, make_draft, confirm, test_engine, dependency) -> None:
    make_sequence()
    draft = make_draft()
    getattr(fakes, dependency).availability.down = True
    response = confirm(draft)
    assert response.status_code == 503
    assert_no_effects(fakes, test_engine, draft)
