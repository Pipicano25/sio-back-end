"""Comparación del precio guardado con el vigente al confirmar (DS-05, P-02; research.md R-07; T010)."""

from __future__ import annotations

from decimal import Decimal as D
from uuid import uuid4

from sales_service.domain.pricing import PriceRef, list_to_request, price_changed

LIST_A, LIST_B, ITEM_1, ITEM_2 = uuid4(), uuid4(), uuid4(), uuid4()


def test_same_price_list_and_item_is_not_a_change() -> None:
    stored = PriceRef(D("16000.0000"), LIST_A, ITEM_1)
    assert not price_changed(stored, PriceRef(D("16000"), LIST_A, ITEM_1))


def test_different_unit_price_is_a_change() -> None:
    assert price_changed(PriceRef(D("16000.0000"), LIST_A, ITEM_1), PriceRef(D("16500.0000"), LIST_A, ITEM_1))


def test_same_price_from_another_list_or_item_is_a_change() -> None:
    """Un cambio de lista o ítem altera la trazabilidad de §8.2 aunque el precio coincida."""
    stored = PriceRef(D("16000.0000"), LIST_A, ITEM_1)
    assert price_changed(stored, PriceRef(D("16000.0000"), LIST_B, ITEM_2))
    assert price_changed(stored, PriceRef(D("16000.0000"), LIST_A, ITEM_2))
    assert price_changed(stored, PriceRef(D("16000.0000"), None, None))


def test_simple_price_unchanged() -> None:
    assert not price_changed(PriceRef(D("12500.0000"), None, None), PriceRef(D("12500.0000"), None, None))


def test_request_sends_the_list_only_when_it_was_requested() -> None:
    """P-02: la confirmación repite la resolución con la intención original."""
    assert list_to_request(price_list_requested=True, price_list_id=LIST_A) == LIST_A
    # Lista resuelta como predeterminada: se vuelve a pedir sin lista, para detectar un cambio de predeterminada.
    assert list_to_request(price_list_requested=False, price_list_id=LIST_A) is None
    assert list_to_request(price_list_requested=False, price_list_id=None) is None
