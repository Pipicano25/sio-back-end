"""`PUT` parcial y versión opcional en borradores (constitución 4.0.0: Principio VII, D9, D10 y D28).

- La cabecera y la línea reciben solo los campos que cambian; lo demás queda igual.
- `version` es opcional: si llega y no coincide, `409`; si no llega, se aplica sobre lo vigente.
- Un cuerpo vacío o con `null` en un campo obligatorio responde `422`; los campos prohibidos
  (`unit_price`, `operation_date`) siguen rechazándose con su código.
"""

from __future__ import annotations

import pytest

from tests.conftest import base, line


def url(world, sale, suffix: str = "") -> str:
    return f"{base(world)}/sales/{sale['id']}{suffix}"


def test_header_put_with_one_field_keeps_the_rest(seller, world, make_draft) -> None:
    draft = make_draft()

    response = seller.put(url(world, draft), json={"observations": "Cliente recoge en tienda"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["observations"] == "Cliente recoge en tienda"
    for field in ("branch_id", "company_customer_id", "payment_method_id"):
        assert body[field] == draft[field]
    assert body["version"] == draft["version"] + 1


def test_header_put_with_stale_version_is_409(seller, world, make_draft) -> None:
    draft = make_draft()
    seller.put(url(world, draft), json={"observations": "Primero"})

    response = seller.put(url(world, draft), json={"observations": "Segundo", "version": draft["version"]})

    assert response.status_code == 409


@pytest.mark.parametrize("payload", [{}, {"version": 1}, {"branch_id": None}, {"desconocido": 1}])
def test_header_body_without_valid_changes_is_422(seller, world, make_draft, payload) -> None:
    draft = make_draft()

    assert seller.put(url(world, draft), json=payload).status_code == 422


def test_header_put_still_rejects_operation_date(seller, world, make_draft) -> None:
    draft = make_draft()

    response = seller.put(url(world, draft), json={"operation_date": "2026-01-01"})

    assert response.status_code == 422
    assert "OPERATION_DATE_NOT_ALLOWED" in response.text


def test_line_put_changes_only_quantity(seller, world, make_draft) -> None:
    draft = make_draft(line(world.product, "2"))
    detail = draft["lines"][0]

    response = seller.put(url(world, draft, f"/details/{detail['id']}"), json={"quantity": "3"})

    assert response.status_code == 200, response.text
    updated = response.json()["lines"][0]
    assert updated["quantity"].startswith("3")
    assert updated["company_product_presentation_id"] == detail["company_product_presentation_id"]


def test_line_put_still_rejects_unit_price(seller, world, make_draft) -> None:
    draft = make_draft(line(world.product, "2"))
    detail = draft["lines"][0]

    response = seller.put(url(world, draft, f"/details/{detail['id']}"), json={"unit_price": "1"})

    assert response.status_code == 422
    assert "UNIT_PRICE_NOT_ALLOWED" in response.text


def test_line_put_keeps_requested_price_list_flag(seller, world, make_draft) -> None:
    """Sin `price_list_id` en el alta, el `PUT` parcial no la vuelve «pedida»."""
    draft = make_draft(line(world.product, "2"))
    detail = draft["lines"][0]

    response = seller.put(url(world, draft, f"/details/{detail['id']}"), json={"quantity": "4"})

    assert response.status_code == 200, response.text
    assert response.json()["lines"][0]["price_list_requested"] is False
