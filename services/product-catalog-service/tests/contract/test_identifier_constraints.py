"""Restricciones de identificadores (RC-07)."""

import pytest
from sqlalchemy.exc import IntegrityError

from product_catalog_service.infrastructure.models import GlobalProductIdentifierModel
from tests import factories


def _products(session_factory):
    unit = factories.unit(session_factory)
    return factories.product(session_factory, unit.id, "Uno"), factories.product(session_factory, unit.id, "Dos")


def test_gtin_family_unique_across_types_and_status(session_factory) -> None:
    first, second = _products(session_factory)
    factories.identifier(session_factory, first.id, "036000291452", "UPC", status="INACTIVE")

    with pytest.raises(IntegrityError, match="uq_global_product_identifiers_gtin_family"):
        factories.identifier(session_factory, second.id, "0036000291452", "EAN")


def test_barcode_unique(session_factory) -> None:
    first, second = _products(session_factory)
    factories.identifier(session_factory, first.id, "XYZ1", "BARCODE")
    with pytest.raises(IntegrityError, match="uq_global_product_identifiers_barcode"):
        factories.identifier(session_factory, second.id, "XYZ1", "BARCODE")


def test_other_unique_per_product(session_factory) -> None:
    first, second = _products(session_factory)
    factories.identifier(session_factory, first.id, "REF-1".replace("-", ""), "OTHER")
    factories.identifier(session_factory, second.id, "REF1", "OTHER")
    with pytest.raises(IntegrityError, match="uq_global_product_identifiers_other"):
        factories.identifier(session_factory, first.id, "REF1", "OTHER")


def test_primary_unique_nulls_not_distinct(session_factory) -> None:
    first, _ = _products(session_factory)

    def primary(value: str):
        return factories._save(
            session_factory,
            GlobalProductIdentifierModel(
                global_product_id=first.id,
                identifier_type="OTHER",
                value=value,
                canonical_value=value,
                is_primary=True,
            ),
        )

    primary("A1")
    with pytest.raises(IntegrityError, match="uq_global_product_identifiers_primary"):
        primary("A2")


def test_presentation_of_other_product_rejected(session_factory) -> None:
    first, second = _products(session_factory)
    foreign = factories.presentation(session_factory, second.id, "CAJA")
    with pytest.raises(IntegrityError, match="fk_global_product_identifiers_presentation_product"):
        factories.identifier(session_factory, first.id, "4006381333931", "EAN", presentation_id=foreign.id)


def test_gtin_format_check(session_factory) -> None:
    first, _ = _products(session_factory)
    with pytest.raises(IntegrityError, match="ck_global_product_identifiers_gtin_format"):
        factories.identifier(session_factory, first.id, "12345", "GTIN")


# ------------------------------------------------------------------ IUM (spec 018)


def test_ium_unique_across_products_and_status(session_factory) -> None:
    first, second = _products(session_factory)
    first_box = factories.presentation(session_factory, first.id, "CAJA")
    second_box = factories.presentation(session_factory, second.id, "CAJA")
    factories.identifier(session_factory, first.id, "2H1005971005105", "IUM", presentation_id=first_box.id, status="INACTIVE")

    with pytest.raises(IntegrityError, match="uq_global_product_identifiers_ium"):
        factories.identifier(session_factory, second.id, "2H1005971005105", "IUM", presentation_id=second_box.id)


def test_ium_requires_presentation_in_database(session_factory) -> None:
    first, _ = _products(session_factory)

    with pytest.raises(IntegrityError, match="ck_global_product_identifiers_ium_format"):
        factories.identifier(session_factory, first.id, "2H1005971005105", "IUM")


def test_ium_format_in_database(session_factory) -> None:
    first, _ = _products(session_factory)
    box = factories.presentation(session_factory, first.id, "CAJA")

    with pytest.raises(IntegrityError, match="ck_global_product_identifiers_ium_format"):
        factories.identifier(session_factory, first.id, "ACTIVO", "IUM", presentation_id=box.id)


def test_unknown_identifier_type_still_rejected(session_factory) -> None:
    first, _ = _products(session_factory)

    with pytest.raises(IntegrityError, match="ck_global_product_identifiers_type"):
        factories.identifier(session_factory, first.id, "X1", "CUM")
