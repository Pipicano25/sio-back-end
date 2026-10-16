"""Una presentación por compra (spec 021, Historia 8; T066; CP-29, CP-30).

`409 DUPLICATE_PRESENTATION_IN_PURCHASE` al crear, al agregar o editar líneas y al confirmar; dos presentaciones del
mismo producto se permiten; si una repetición llega a la base (`uq_purchase_details_purchase_presentation`), también
responde `409`. Datos ficticios.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from purchase_service.application import purchase_service as purchase_module
from purchase_service.application.exceptions import DuplicatePresentationInPurchaseError
from purchase_service.application.reference_validation import check_unique_presentations
from tests.conftest import base, count_rows, line, purchase_body

CODE = "DUPLICATE_PRESENTATION_IN_PURCHASE"


def _assert_duplicate(response) -> dict:
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"].endswith(CODE)
    return body


def test_cp29_create_with_a_repeated_presentation(buyer, world, test_engine) -> None:
    response = buyer.post(f"{base(world)}/purchases", json=purchase_body(
        world, line(world.product, "2"), line(world.product_2, "1"), line(world.product, "3"),
    ))
    body = _assert_duplicate(response)
    [error] = body["errors"]
    assert error["field"] == "lines[2].company_product_presentation_id" and error["line_number"] == 3
    assert "línea 1" in error["message"]
    assert count_rows(test_engine, "purchases") == 0


def test_cp29_add_a_line_with_a_presentation_already_in_the_purchase(buyer, world, make_draft, test_engine) -> None:
    draft = make_draft(line(world.product))
    response = buyer.post(f"{base(world)}/purchases/{draft['id']}/details",
                          json={**line(world.product, "5"), "version": draft["version"]})
    _assert_duplicate(response)
    assert count_rows(test_engine, "purchase_details") == 1
    assert buyer.get(f"{base(world)}/purchases/{draft['id']}").json()["version"] == draft["version"]


def test_cp29_edit_a_line_to_a_presentation_of_another_line(buyer, world, make_draft) -> None:
    draft = make_draft(line(world.product), line(world.product_2))
    second = draft["lines"][1]
    response = buyer.put(f"{base(world)}/purchases/{draft['id']}/details/{second['id']}",
                         json={**line(world.product, "4"), "version": draft["version"]})
    _assert_duplicate(response)
    same = buyer.put(f"{base(world)}/purchases/{draft['id']}/details/{second['id']}",
                     json={**line(world.product_2, "4"), "version": draft["version"]})
    assert same.status_code == 200, same.text  # la línea puede conservar su propia presentación


def test_cp30_two_presentations_of_the_same_product_are_allowed(buyer, world, make_draft) -> None:
    draft = make_draft(
        line(world.product, "2"),
        line(world.product, "1", company_product_presentation_id=world.presentation),
    )
    assert [item["company_product_presentation_id"] for item in draft["lines"]] == [
        str(line(world.product)["company_product_presentation_id"]), str(world.presentation)
    ]


def test_a_repetition_that_reaches_the_database_is_translated(buyer, world, make_draft, monkeypatch, test_engine) -> None:
    """Sin la validación de la aplicación (p. ej. dos ediciones concurrentes), la restricción única responde `409`."""
    draft = make_draft(line(world.product))
    monkeypatch.setattr(purchase_module, "check_unique_presentations", lambda lines: None)
    response = buyer.post(f"{base(world)}/purchases/{draft['id']}/details",
                          json={**line(world.product, "5"), "version": draft["version"]})
    _assert_duplicate(response)
    assert count_rows(test_engine, "purchase_details") == 1


def test_confirmation_check_reports_every_repeated_line() -> None:
    """La confirmación aplica la misma regla (defensiva: la base ya impide guardar un borrador con repeticiones)."""
    presentation, other = uuid4(), uuid4()
    with pytest.raises(DuplicatePresentationInPurchaseError) as raised:
        check_unique_presentations([
            ("lines[0].company_product_presentation_id", 1, presentation),
            ("lines[1].company_product_presentation_id", 2, other),
            ("lines[2].company_product_presentation_id", 3, presentation),
            ("lines[3].company_product_presentation_id", 4, presentation),
        ])
    assert [error["line_number"] for error in raised.value.errors] == [3, 4]
    check_unique_presentations([("x", 1, presentation), ("y", 2, other), ("z", 3, None)])  # sin repeticiones
