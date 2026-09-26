"""Restricciones de valores de atributo (RC-05, DS-09)."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from tests import factories


def _setup(session_factory):
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id)
    color = factories.definition(session_factory, "COLOR", "OPTION")
    size = factories.definition(session_factory, "SIZE", "OPTION")
    red = factories.option(session_factory, color.id, "RED")
    return product, color, size, red


def test_exactly_one_value(session_factory) -> None:
    product, color, _, red = _setup(session_factory)

    with pytest.raises(IntegrityError, match="ck_global_product_attribute_values_exactly_one"):
        factories.value(session_factory, product.id, color.id)
    with pytest.raises(IntegrityError, match="ck_global_product_attribute_values_exactly_one"):
        factories.value(session_factory, product.id, color.id, option_id=red.id, text_value="rojo")


def test_option_must_belong_to_definition(session_factory) -> None:
    product, _, size, red = _setup(session_factory)

    with pytest.raises(IntegrityError, match="fk_global_product_attribute_values_option_definition"):
        factories.value(session_factory, product.id, size.id, option_id=red.id)


def test_single_value_per_definition(session_factory) -> None:
    product, _, _, _ = _setup(session_factory)
    fat = factories.definition(session_factory, "GRASA")
    factories.value(session_factory, product.id, fat.id, decimal_value=Decimal("1"))

    with pytest.raises(IntegrityError, match="uq_global_product_attribute_values_product_definition"):
        factories.value(session_factory, product.id, fat.id, decimal_value=Decimal("2"))
