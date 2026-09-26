"""Fábricas de datos de prueba.

Las pruebas de una historia pueden crear por base de datos los elementos que
administra otra historia (p. ej. presentaciones para la completitud en US3).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from product_catalog_service.infrastructure import models

ACTOR = "fixture"


def _stamp(entity):
    now = datetime.now(UTC)
    entity.created_at = now
    entity.updated_at = now
    entity.created_by = ACTOR
    entity.updated_by = ACTOR
    return entity


def _save(factory: sessionmaker, entity):
    with factory() as session:
        session.add(_stamp(entity))
        session.commit()
        session.refresh(entity)
        session.expunge(entity)
    return entity


def unit(factory: sessionmaker, code: str = "UND", *, status: str = "ACTIVE", allows_decimals: bool = False):
    return _save(
        factory,
        models.GlobalUnitOfMeasureModel(
            code=code,
            name=code.title(),
            symbol=code.lower(),
            measurement_type="UNIT",
            allows_decimals=allows_decimals,
            status=status,
        ),
    )


def brand(factory: sessionmaker, code: str = "ACME", *, status: str = "ACTIVE"):
    return _save(factory, models.GlobalBrandModel(code=code, name=code.title(), status=status))


def packaging(factory: sessionmaker, code: str = "BOX", *, status: str = "ACTIVE"):
    return _save(factory, models.GlobalPackagingTypeModel(code=code, name=code.title(), status=status))


def category(factory: sessionmaker, code: str, *, parent: UUID | None = None, status: str = "ACTIVE"):
    return _save(
        factory,
        models.GlobalCategoryModel(code=code, name=code.title(), parent_category_id=parent, status=status),
    )


def product(
    factory: sessionmaker,
    base_unit_id: UUID,
    name: str = "Arroz blanco 500 g",
    *,
    brand_id: UUID | None = None,
    status: str = "ACTIVE",
    first_used: bool = False,
):
    from product_catalog_service.application.normalization import canonical_name_key

    entity = models.GlobalProductModel(
        product_type="GOOD",
        canonical_name=name,
        canonical_name_key=canonical_name_key(name),
        base_unit_id=base_unit_id,
        global_brand_id=brand_id,
        status=status,
    )
    if first_used:
        entity.first_used_at = datetime.now(UTC)
        entity.first_used_by = ACTOR
        entity.first_use_source = "MANUAL"
    return _save(factory, entity)


def product_category(
    factory: sessionmaker,
    product_id: UUID,
    category_id: UUID,
    *,
    is_primary: bool = True,
    status: str = "ACTIVE",
):
    return _save(
        factory,
        models.GlobalProductCategoryModel(
            global_product_id=product_id,
            global_category_id=category_id,
            is_primary=is_primary,
            status=status,
        ),
    )


def definition(
    factory: sessionmaker,
    code: str,
    data_type: str = "DECIMAL",
    *,
    status: str = "ACTIVE",
    unit_id: UUID | None = None,
):
    return _save(
        factory,
        models.ProductAttributeDefinitionModel(
            code=code,
            name=code.title(),
            description=f"Definición {code}",
            data_type=data_type,
            unit_of_measure_id=unit_id,
            status=status,
        ),
    )


def option(factory: sessionmaker, definition_id: UUID, code: str, *, status: str = "ACTIVE"):
    return _save(
        factory,
        models.ProductAttributeOptionModel(
            attribute_definition_id=definition_id,
            code=code,
            name=code.title(),
            status=status,
        ),
    )


def category_attribute(
    factory: sessionmaker,
    category_id: UUID,
    definition_id: UUID,
    *,
    required: bool = True,
    filterable: bool = False,
    status: str = "ACTIVE",
):
    return _save(
        factory,
        models.GlobalCategoryAttributeModel(
            global_category_id=category_id,
            attribute_definition_id=definition_id,
            is_required=required,
            is_filterable=filterable,
            status=status,
        ),
    )


def value(factory: sessionmaker, product_id: UUID, definition_id: UUID, **typed):
    return _save(
        factory,
        models.GlobalProductAttributeValueModel(
            global_product_id=product_id,
            attribute_definition_id=definition_id,
            **typed,
        ),
    )


def presentation(
    factory: sessionmaker,
    product_id: UUID,
    code: str = "UNIDAD",
    *,
    base_quantity: Decimal = Decimal("1"),
    status: str = "ACTIVE",
    is_base: bool = False,
    first_used: bool = False,
):
    entity = models.GlobalProductPresentationModel(
        global_product_id=product_id,
        code=code,
        name=code.title(),
        base_quantity=base_quantity,
        status=status,
        is_base=is_base,
    )
    if first_used:
        entity.first_used_at = datetime.now(UTC)
        entity.first_used_by = ACTOR
        entity.first_use_source = "MANUAL"
    return _save(factory, entity)


def identifier(
    factory: sessionmaker,
    product_id: UUID,
    value: str,
    identifier_type: str = "GTIN",
    *,
    presentation_id: UUID | None = None,
    status: str = "ACTIVE",
):
    from product_catalog_service.domain.gtin import canonical_value

    return _save(
        factory,
        models.GlobalProductIdentifierModel(
            global_product_id=product_id,
            global_product_presentation_id=presentation_id,
            identifier_type=identifier_type,
            value=value,
            canonical_value=canonical_value(identifier_type, value),
            status=status,
        ),
    )


def complete_product(factory: sessionmaker, name: str = "Leche entera 1 L", **kwargs):
    """Producto completo: unidad, categoría principal y una presentación activa."""
    base_unit = kwargs.pop("base_unit", None) or unit(factory, f"U{abs(hash(name)) % 10**6}")
    cat = kwargs.pop("category", None) or category(factory, f"C{abs(hash(name)) % 10**6}")
    created = product(factory, base_unit.id, name, **kwargs)
    product_category(factory, created.id, cat.id)
    presentation(factory, created.id)
    return created, cat, base_unit


def session_value(session: Session, model, entity_id: UUID):
    return session.get(model, entity_id)


def today() -> date:
    return date.today()
