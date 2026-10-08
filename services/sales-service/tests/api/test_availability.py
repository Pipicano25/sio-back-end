"""Disponibilidad de existencias de un borrador (Historia 4; FR-013; research.md R-08; T048)."""

from __future__ import annotations

from uuid import uuid4

from tests.conftest import base, count_rows, line


def url(world, sale) -> str:
    return f"{base(world)}/sales/{sale['id']}/availability"


def test_required_is_aggregated_by_product_in_base_units(seller, world, make_draft, fakes, test_engine) -> None:
    fakes.inventory.layers.clear()
    fakes.inventory.stock(world.branch, world.product, "20", "1000")
    draft = make_draft(
        line(world.product, "2"),  # 2 unidades
        line(world.product_2, "1"),  # sin saldo
        line(world.product, "2", company_product_presentation_id=world.presentation),  # 2 cajas × 12 = 24
    )
    response = seller.get(url(world, draft))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sale_id"] == draft["id"] and body["branch_id"] == str(world.branch)
    assert body["all_available"] is False
    rice, oil = body["products"]
    assert rice == {
        "company_product_id": str(world.product),
        "line_numbers": [1, 3],
        "required_base_quantity": "26.0000",
        "available_base_quantity": "20.0000",
        "is_available": False,
    }
    assert oil["available_base_quantity"] == "0.0000" and oil["required_base_quantity"] == "1.0000"
    # No reserva ni escribe: el saldo no cambia y no hay operaciones.
    assert fakes.inventory.balance(world.branch, world.product) == 20
    assert count_rows(test_engine, "sale_operations") == 0
    assert [call[0] for call in fakes.inventory.availability.calls] == ["balances"]


def test_all_available(seller, world, make_draft) -> None:
    body = seller.get(url(world, make_draft(line(world.product, "5")))).json()
    assert body["all_available"] is True and body["products"][0]["is_available"] is True


def test_inventory_unavailable_is_503(seller, world, make_draft, fakes) -> None:
    draft = make_draft()
    fakes.inventory.availability.down = True
    response = seller.get(url(world, draft))
    assert response.status_code == 503 and response.json()["dependency"] == "inventory"


def test_readers_with_membership_can_consult_without_branch_assignment(as_user, world, make_draft) -> None:
    draft = make_draft()
    assert as_user("reportes.test").get(url(world, draft)).status_code == 200


def test_permission_membership_and_isolation(as_user, world, make_draft, fakes) -> None:
    draft = make_draft()
    assert as_user("compras.test").get(url(world, draft)).status_code == 403
    assert as_user("ventas.test").get(f"{base(world)}/sales/{uuid4()}/availability").status_code == 404
    from tests.conftest import user_sub

    fakes.oc.members.pop((user_sub("reportes.test"), world.company))
    assert as_user("reportes.test").get(url(world, draft)).status_code == 404
