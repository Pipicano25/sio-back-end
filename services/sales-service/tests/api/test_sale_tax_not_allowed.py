"""Ventas sin impuesto adicional durante el MVP (spec 021, B-4 provisional; FR-021-30; CP-63).

El precio de la lista es el importe final que paga el cliente: `tax_amount` solo admite 0 al crear, al agregar o
editar líneas. **No es una solución fiscal** (no separa el impuesto incluido ni factura).
"""

from __future__ import annotations

from tests.conftest import base, count_rows, line, sale_body


def first_error(response) -> dict:
    return response.json()["errors"][0]


def test_cp63_tax_is_rejected_when_creating_adding_and_editing_lines(seller, world, make_draft, test_engine) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product, tax_amount="5700")))
    assert response.status_code == 422
    assert first_error(response)["code"] == "TAX_NOT_ALLOWED" and first_error(response)["field"] == "lines[0].tax_amount"

    draft = make_draft(line(world.product))
    added = seller.post(f"{base(world)}/sales/{draft['id']}/details", json={**line(world.product_2, tax_amount="0.01"), "version": 1})
    assert added.status_code == 422 and first_error(added)["code"] == "TAX_NOT_ALLOWED"
    detail = draft["lines"][0]
    edited = seller.put(f"{base(world)}/sales/{draft['id']}/details/{detail['id']}",
                        json={**line(world.product, "2", tax_amount="100"), "version": 1})
    assert edited.status_code == 422 and first_error(edited)["code"] == "TAX_NOT_ALLOWED"
    assert count_rows(test_engine, "sale_details") == 1


def test_zero_or_omitted_tax_keeps_the_final_list_price(seller, world) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product, "2", tax_amount="0"), line(world.product_2)))
    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["tax_total"] == "0.00" and sale["total"] == sale["subtotal"]
    assert all(item["tax_amount"] == "0.00" and item["total"] == item["subtotal"] for item in sale["lines"])
