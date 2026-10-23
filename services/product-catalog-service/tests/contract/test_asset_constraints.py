"""Restricciones de activos (las de imágenes por presentación: `test_presentation_image_constraints.py`)."""

import pytest
from sqlalchemy.exc import IntegrityError

from product_catalog_service.infrastructure.models import ProductAssetModel
from tests import factories


def _asset(session_factory, product_id, **fields):
    data = {
        "global_product_id": product_id,
        "asset_type": "TECHNICAL_SHEET",
        "file_name": "a.png",
        "storage_uri": "s3://b/a.png",
        **fields,
    }
    return factories._save(session_factory, ProductAssetModel(**data))


def _product(session_factory):
    unit = factories.unit(session_factory)
    return factories.product(session_factory, unit.id)


def test_single_active_primary_per_type(session_factory) -> None:
    product = _product(session_factory)
    _asset(session_factory, product.id, is_primary=True)
    _asset(session_factory, product.id, is_primary=True, asset_type="MANUAL")
    _asset(session_factory, product.id, is_primary=False)

    with pytest.raises(IntegrityError, match="uq_product_assets_primary"):
        _asset(session_factory, product.id, is_primary=True)


def test_primary_must_be_active(session_factory) -> None:
    product = _product(session_factory)
    with pytest.raises(IntegrityError, match="ck_product_assets_primary_active"):
        _asset(session_factory, product.id, is_primary=True, status="INACTIVE")


def test_asset_type_check(session_factory) -> None:
    product = _product(session_factory)
    with pytest.raises(IntegrityError, match="ck_product_assets_asset_type"):
        _asset(session_factory, product.id, asset_type="VIDEO")
