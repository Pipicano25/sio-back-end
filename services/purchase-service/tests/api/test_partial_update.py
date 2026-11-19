"""`PUT` parcial y versión opcional en borradores (constitución 4.0.0: Principio VII, D9, D10 y D28).

- La cabecera y la línea reciben solo los campos que cambian; lo demás queda igual.
- `version` es opcional: si llega y no coincide, `409`; si no llega, se aplica sobre lo vigente.
- Un cuerpo vacío o con `null` en un campo obligatorio responde `422`.
- Borrar una línea no exige `version`.
"""

from __future__ import annotations

import pytest

from tests.conftest import base, line


def url(world, purchase, suffix: str = "") -> str:
    return f"{base(world)}/purchases/{purchase['id']}{suffix}"


def test_header_put_with_one_field_keeps_the_rest(buyer, world, make_draft) -> None:
    draft = make_draft()

    response = buyer.put(url(world, draft), json={"observations": "Entregar en bodega"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["observations"] == "Entregar en bodega"
    for field in ("branch_id", "company_supplier_id", "operation_date", "payment_method_id"):
        assert body[field] == draft[field]
    assert body["version"] == draft["version"] + 1


def test_header_put_with_stale_version_is_409(buyer, world, make_draft) -> None:
    draft = make_draft()
    buyer.put(url(world, draft), json={"observations": "Primero"})

    response = buyer.put(url(world, draft), json={"observations": "Segundo", "version": draft["version"]})

    assert response.status_code == 409
    assert response.json()["code"] == "PURCHASE.VERSION_CONFLICT"


@pytest.mark.parametrize("payload", [{}, {"version": 1}, {"branch_id": None}, {"desconocido": 1}])
def test_header_body_without_valid_changes_is_422(buyer, world, make_draft, payload) -> None:
    draft = make_draft()

    assert buyer.put(url(world, draft), json=payload).status_code == 422


def test_line_put_changes_only_quantity(buyer, world, make_draft) -> None:
    draft = make_draft(line(world.product, "2", "100"))
    detail = draft["lines"][0]

    response = buyer.put(url(world, draft, f"/details/{detail['id']}"), json={"quantity": "5"})

    assert response.status_code == 200, response.text
    updated = response.json()["lines"][0]
    assert updated["quantity"].startswith("5")
    assert updated["unit_cost"] == detail["unit_cost"]
    assert updated["company_product_presentation_id"] == detail["company_product_presentation_id"]


def test_line_delete_without_version(buyer, world, make_draft) -> None:
    draft = make_draft(line(world.product, "2", "100"))
    added = buyer.post(url(world, draft, "/details"), json=line(world.product_2, "1", "50")).json()

    response = buyer.delete(url(world, draft, f"/details/{added['lines'][0]['id']}"))

    assert response.status_code == 200, response.text
    assert len(response.json()["lines"]) == 1
