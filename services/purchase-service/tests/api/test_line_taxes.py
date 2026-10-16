"""Historia 4 de la spec 021 (Purchase): impuesto de compra por tasa (T027; FR-021-09..12; DS-03, DS-04).

CP-31, CP-32, CP-33, CP-34, CP-61, CP-62, CP-65. Tasas ficticias de los dobles: arroz 19 %, aceite 0 % (el 19 % no es
una tarifa real).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from tests.conftest import base, fetch, line

def _line(world, product=None, **extra):
    product = product or world.product
    return line(product, extra.pop("quantity", "2"), extra.pop("unit_cost", "120000"), **extra)


def _set_tax(fakes, product, tax):
    fakes.cr.products[product] = replace(fakes.cr.products[product], purchase_tax_percentage=tax)


def test_tax_is_computed_from_the_product_rate(make_draft, world) -> None:
    draft = make_draft(_line(world))
    [detail] = draft["lines"]
    # (2 × 120.000 − 0) × 19 % = 45.600 → total 285.600.
    assert detail["tax_percentage"] == "19.0000" and detail["tax_percentage_source"] == "PRODUCT_DEFAULT"
    assert detail["tax_amount"] == "45600.00" and detail["total"] == "285600.00"
    assert detail["warnings"] == []
    assert draft["tax_total"] == "45600.00" and draft["total"] == "285600.00"


def test_tax_applies_after_discount(make_draft, world) -> None:
    draft = make_draft(_line(world, discount_amount="24000"))
    [detail] = draft["lines"]
    # (240.000 − 24.000) × 19 % = 41.040; total = 216.000 + 41.040.
    assert detail["tax_amount"] == "41040.00" and detail["total"] == "257040.00"


def test_client_cannot_send_tax_amount(buyer, world) -> None:
    from tests.conftest import purchase_body

    response = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, _line(world, tax_amount="45600")))
    assert response.status_code == 422, response.text
    assert "tax_amount" in response.text


def test_cp33_different_rates_in_one_purchase(make_draft, world) -> None:
    draft = make_draft(_line(world), line(world.product_2, "3", "1000"))
    arroz, aceite = draft["lines"]
    assert (arroz["tax_percentage"], arroz["tax_amount"]) == ("19.0000", "45600.00")
    assert (aceite["tax_percentage"], aceite["tax_amount"]) == ("0.0000", "0.00")  # CP-32: 0 % explícito


def test_cp31_not_configured_is_a_warning_in_draft_and_blocks_confirmation(make_draft, confirm, make_sequence, world, fakes, buyer) -> None:
    make_sequence()
    _set_tax(fakes, world.product, None)
    draft = make_draft(_line(world))
    [detail] = draft["lines"]
    assert detail["tax_percentage"] is None and detail["tax_percentage_source"] is None
    assert detail["tax_amount"] == "0.00" and detail["warnings"] == ["PURCHASE_TAX_NOT_CONFIGURED"]

    response = confirm(draft)
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"].endswith("PURCHASE_TAX_NOT_CONFIGURED")
    assert body["errors"][0]["line_number"] == 1
    current = buyer.get(f"{base(world)}/purchases/{draft['id']}").json()
    assert current["status"] == "DRAFT" and current["version"] == draft["version"]  # sin efectos


def test_cp31_draft_is_kept_and_confirms_once_configured(make_draft, confirm, make_sequence, world, fakes, buyer) -> None:
    make_sequence()
    _set_tax(fakes, world.product, None)
    draft = make_draft(_line(world))
    assert confirm(draft).status_code == 409
    assert buyer.get(f"{base(world)}/purchases/{draft['id']}").json()["status"] == "DRAFT"

    _set_tax(fakes, world.product, Decimal("19"))
    # La línea guardada sin tasa no se completa sola al confirmar: se vuelve a guardar (el impuesto no cambia a escondidas).
    response = confirm(draft)
    assert response.status_code == 409 and response.json()["code"].endswith("PURCHASE_TAX_NOT_CONFIGURED")
    detail = draft["lines"][0]
    saved = buyer.put(
        f"{base(world)}/purchases/{draft['id']}/details/{detail['id']}",
        json={**_line(world), "version": draft["version"]},
    )
    assert saved.status_code == 200, saved.text
    confirmed = confirm(saved.json())
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["lines"][0]["tax_percentage"] == "19.0000"


def test_cp65_default_rate_changed_between_draft_and_confirmation(make_draft, confirm, make_sequence, world, fakes) -> None:
    make_sequence()
    draft = make_draft(_line(world))
    _set_tax(fakes, world.product, Decimal("5"))
    response = confirm(draft)
    assert response.status_code == 409, response.text
    error = response.json()["errors"][0]
    assert error["code"] == "PURCHASE_TAX_CHANGED" and "19" in error["message"] and "5" in error["message"]


def test_cp34_confirmed_purchase_keeps_its_rate(make_draft, confirm, make_sequence, world, fakes, buyer) -> None:
    make_sequence()
    confirmed = confirm(make_draft(_line(world))).json()
    _set_tax(fakes, world.product, Decimal("5"))
    current = buyer.get(f"{base(world)}/purchases/{confirmed['id']}").json()
    assert current["lines"][0]["tax_percentage"] == "19.0000" and current["lines"][0]["tax_amount"] == "45600.00"


def test_cp61_override_requires_permission_and_is_audited(as_user, make_draft, world, test_engine) -> None:
    from tests.conftest import purchase_body

    body = purchase_body(world, _line(world, tax_percentage="5"))
    assert as_user("compras.test").post(f"{base(world)}/purchases", json=body).status_code == 403

    supervisor = as_user("supervisor.test")
    response = supervisor.post(f"{base(world)}/purchases", json=body)
    assert response.status_code == 201, response.text
    [detail] = response.json()["lines"]
    assert detail["tax_percentage"] == "5.0000" and detail["tax_percentage_source"] == "LINE_OVERRIDE"
    assert detail["tax_amount"] == "12000.00"
    events = [row["payload"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox ORDER BY created_at")]
    override = [event for event in events if event["action"] == "OVERRIDE_PURCHASE_LINE_TAX"]
    assert len(override) == 1
    assert override[0]["previous_values"] == {"tax_percentage": "19.0000"}
    assert override[0]["new_values"]["tax_percentage"] == "5.0000"


def test_cp61_override_on_an_existing_line(as_user, make_draft, world, fakes) -> None:
    draft = make_draft(_line(world))
    supervisor = as_user("supervisor.test")
    detail = draft["lines"][0]
    url = f"{base(world)}/purchases/{draft['id']}/details/{detail['id']}"
    updated = supervisor.put(url, json={**_line(world, tax_percentage="0"), "version": draft["version"]})
    assert updated.status_code == 200, updated.text
    assert updated.json()["lines"][0]["tax_amount"] == "0.00"
    assert updated.json()["lines"][0]["tax_percentage_source"] == "LINE_OVERRIDE"
    assert fakes.cr.products[world.product].purchase_tax_percentage == Decimal("19")  # el producto no cambia


@pytest.mark.parametrize("value", ["-1", "100.0001", "12.34567", "abc"])
def test_cp62_override_out_of_range(as_user, world, value) -> None:
    from tests.conftest import purchase_body

    response = as_user("supervisor.test").post(
        f"{base(world)}/purchases", json=purchase_body(world, _line(world, tax_percentage=value))
    )
    assert response.status_code == 422, response.text
    assert "TAX_PERCENTAGE_OUT_OF_RANGE" in response.text
