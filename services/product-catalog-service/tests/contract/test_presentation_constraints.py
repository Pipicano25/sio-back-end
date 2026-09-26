"""Restricciones de presentaciones (RC-06)."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from product_catalog_service.infrastructure.models import GlobalProductPresentationModel
from tests import factories


def _product(session_factory):
    unit = factories.unit(session_factory)
    return factories.product(session_factory, unit.id)


def _presentation(session_factory, product_id, **fields):
    data = {"global_product_id": product_id, "code": "P", "name": "P", "base_quantity": Decimal("1"), **fields}
    return factories._save(session_factory, GlobalProductPresentationModel(**data))


@pytest.mark.parametrize(
    ("fields", "constraint"),
    [
        ({"base_quantity": Decimal("0")}, "ck_global_product_presentations_base_quantity_positive"),
        ({"content_quantity": Decimal("120")}, "ck_global_product_presentations_content_pair"),
        ({"content_quantity": Decimal("-1"), "content_unit_id": None}, "ck_global_product_presentations_content_pair"),
        ({"is_base": True, "base_quantity": Decimal("20")}, "ck_global_product_presentations_base_factor"),
        ({"is_base": True, "status": "INACTIVE"}, "ck_global_product_presentations_base_active"),
        ({"display_order": -1}, "ck_global_product_presentations_display_order"),
    ],
)
def test_checks(session_factory, fields, constraint) -> None:
    product = _product(session_factory)
    with pytest.raises(IntegrityError, match=constraint):
        _presentation(session_factory, product.id, **fields)


def test_content_positive(session_factory) -> None:
    product = _product(session_factory)
    unit = factories.unit(session_factory, "ML")
    with pytest.raises(IntegrityError, match="ck_global_product_presentations_content_positive"):
        _presentation(session_factory, product.id, content_quantity=Decimal("0"), content_unit_id=unit.id)


def test_code_unique_including_inactive(session_factory) -> None:
    product = _product(session_factory)
    _presentation(session_factory, product.id, code="CAJA", status="INACTIVE")
    with pytest.raises(IntegrityError, match="uq_global_product_presentations_product_code"):
        _presentation(session_factory, product.id, code="CAJA")


def test_single_active_base(session_factory) -> None:
    product = _product(session_factory)
    _presentation(session_factory, product.id, code="A", is_base=True)
    with pytest.raises(IntegrityError, match="uq_global_product_presentations_base"):
        _presentation(session_factory, product.id, code="B", is_base=True)
