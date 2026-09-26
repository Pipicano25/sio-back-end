"""Restricciones de la clasificación producto–categoría (RC-04)."""

import pytest
from sqlalchemy.exc import IntegrityError

from product_catalog_service.infrastructure.models import GlobalProductCategoryModel
from tests import factories


def _setup(session_factory):
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id)
    first = factories.category(session_factory, "A")
    second = factories.category(session_factory, "B")
    return product, first, second


def test_only_one_active_primary(session_factory) -> None:
    product, first, second = _setup(session_factory)
    factories.product_category(session_factory, product.id, first.id, is_primary=True)

    with pytest.raises(IntegrityError, match="uq_global_product_categories_primary"):
        factories.product_category(session_factory, product.id, second.id, is_primary=True)


def test_primary_must_be_active(session_factory) -> None:
    product, first, _ = _setup(session_factory)

    with pytest.raises(IntegrityError, match="ck_global_product_categories_primary_active"):
        factories.product_category(session_factory, product.id, first.id, is_primary=True, status="INACTIVE")


def test_pair_is_unique(session_factory) -> None:
    product, first, _ = _setup(session_factory)
    factories.product_category(session_factory, product.id, first.id)

    with pytest.raises(IntegrityError, match="uq_global_product_categories_product_category"):
        factories.product_category(session_factory, product.id, first.id, is_primary=False)

    with session_factory() as session:
        assert session.query(GlobalProductCategoryModel).count() == 1
