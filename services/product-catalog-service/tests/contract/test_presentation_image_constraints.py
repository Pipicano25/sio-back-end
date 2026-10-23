"""Restricciones de la base para imágenes por presentación (spec 024, casos 29 y 30; FR-024-01 a FR-024-05)."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from tests import factories
from tests.spec022_support import image_asset


@pytest.fixture
def catalog(session_factory):
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, "Gaseosa cola")
    other = factories.product(session_factory, unit.id, "Gaseosa naranja")
    bottle = factories.presentation(session_factory, product.id, "BOTELLA")
    can = factories.presentation(session_factory, product.id, "LATA")
    foreign = factories.presentation(session_factory, other.id, "BOTELLA")
    return product, bottle, can, foreign


def test_image_without_presentation_is_rejected(session_factory, catalog) -> None:
    product, *_ = catalog
    with pytest.raises(IntegrityError, match="ck_product_assets_image_requires_presentation"):
        image_asset(session_factory, product.id, presentation_id=None)


def test_presentation_of_other_product_is_rejected(session_factory, catalog) -> None:
    product, _, _, foreign = catalog
    with pytest.raises(IntegrityError, match="fk_product_assets_presentation_product"):
        image_asset(session_factory, product.id, presentation_id=foreign.id)


def test_two_active_primaries_in_a_presentation_are_rejected(session_factory, catalog) -> None:
    product, bottle, *_ = catalog
    image_asset(session_factory, product.id, presentation_id=bottle.id, content=b"\x89PNG\r\n\x1a\nuno")
    with pytest.raises(IntegrityError, match="uq_product_assets_presentation_primary"):
        image_asset(session_factory, product.id, presentation_id=bottle.id, content=b"\x89PNG\r\n\x1a\ndos")


def test_each_presentation_has_its_own_primary(session_factory, catalog) -> None:
    product, bottle, can, _ = catalog
    image_asset(session_factory, product.id, presentation_id=bottle.id, content=b"\x89PNG\r\n\x1a\nuno")
    image_asset(session_factory, product.id, presentation_id=can.id, content=b"\x89PNG\r\n\x1a\ndos")


def test_non_image_cannot_have_presentation(session_factory, catalog) -> None:
    product, bottle, *_ = catalog
    with pytest.raises(IntegrityError, match="ck_product_assets_presentation_only_image"):
        image_asset(session_factory, product.id, presentation_id=bottle.id, asset_type="MANUAL", mime="application/pdf")


def test_non_image_keeps_primary_per_product_and_type(session_factory, catalog) -> None:
    product, *_ = catalog
    image_asset(session_factory, product.id, asset_type="MANUAL", mime="application/pdf", content=b"uno")
    with pytest.raises(IntegrityError, match="uq_product_assets_primary"):
        image_asset(session_factory, product.id, asset_type="MANUAL", mime="application/pdf", content=b"dos")
