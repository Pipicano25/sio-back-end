"""Restricciones de definiciones, opciones y atributos por categoría."""

import pytest
from sqlalchemy.exc import IntegrityError

from tests import factories


def test_unit_only_for_numeric_definitions(session_factory) -> None:
    unit = factories.unit(session_factory, "KG")
    with pytest.raises(IntegrityError, match="ck_product_attribute_definitions_unit_numeric"):
        factories.definition(session_factory, "NOMBRE", "TEXT", unit_id=unit.id)


def test_description_not_blank(session_factory) -> None:
    from product_catalog_service.infrastructure.models import ProductAttributeDefinitionModel

    with pytest.raises(IntegrityError, match="ck_product_attribute_definitions_description_not_blank"):
        factories._save(
            session_factory,
            ProductAttributeDefinitionModel(code="X", name="X", description="  ", data_type="TEXT"),
        )


def test_option_code_unique_per_definition(session_factory) -> None:
    color = factories.definition(session_factory, "COLOR", "OPTION")
    size = factories.definition(session_factory, "SIZE", "OPTION")
    factories.option(session_factory, color.id, "RED")
    factories.option(session_factory, size.id, "RED")

    with pytest.raises(IntegrityError, match="uq_product_attribute_options_definition_code"):
        factories.option(session_factory, color.id, "RED")


def test_category_attribute_pair_unique(session_factory) -> None:
    category = factories.category(session_factory, "LECHES")
    definition = factories.definition(session_factory, "GRASA")
    factories.category_attribute(session_factory, category.id, definition.id)

    with pytest.raises(IntegrityError, match="uq_global_category_attributes_category_definition"):
        factories.category_attribute(session_factory, category.id, definition.id)


def test_display_order_not_negative(session_factory) -> None:
    from product_catalog_service.infrastructure.models import GlobalCategoryAttributeModel

    category = factories.category(session_factory, "LECHES")
    definition = factories.definition(session_factory, "GRASA")
    with pytest.raises(IntegrityError, match="ck_global_category_attributes_display_order"):
        factories._save(
            session_factory,
            GlobalCategoryAttributeModel(
                global_category_id=category.id,
                attribute_definition_id=definition.id,
                display_order=-1,
            ),
        )
