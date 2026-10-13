"""Migraciones y restricciones nombradas (Principio VIII, puerta de calidad 3)."""

from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from tests.conftest import FUNCTIONAL_TABLES, build_alembic_config

EXPECTED_CONSTRAINTS = {
    "uq_global_units_of_measure_code",
    "ck_global_units_of_measure_code_normalized",
    "ck_global_units_of_measure_measurement_type",
    "ck_global_units_of_measure_status",
    "uq_global_packaging_types_code",
    "uq_global_brands_code",
    "uq_global_categories_code",
    "ck_global_categories_not_self_parent",
    "ck_global_products_product_type",
    "ck_global_products_first_use_consistent",
    "ck_global_products_first_use_source",
    "uq_global_product_categories_product_category",
    "ck_global_product_categories_primary_active",
    "uq_product_attribute_definitions_code",
    "ck_product_attribute_definitions_data_type",
    "ck_product_attribute_definitions_unit_numeric",
    "ck_product_attribute_definitions_description_not_blank",
    "uq_product_attribute_options_definition_code",
    "uq_product_attribute_options_id_definition",
    "ck_product_attribute_options_display_order",
    "uq_global_category_attributes_category_definition",
    "ck_global_category_attributes_display_order",
    "uq_global_product_attribute_values_product_definition",
    "ck_global_product_attribute_values_exactly_one",
    "ck_global_product_attribute_values_text_not_blank",
    "fk_global_product_attribute_values_option_definition",
    "uq_global_product_presentations_product_code",
    "uq_global_product_presentations_id_product",
    "ck_global_product_presentations_base_quantity_positive",
    "ck_global_product_presentations_content_pair",
    "ck_global_product_presentations_content_positive",
    "ck_global_product_presentations_base_factor",
    "ck_global_product_presentations_base_active",
    "ck_global_product_presentations_display_order",
    "ck_global_product_presentations_first_use_consistent",
    "fk_global_product_identifiers_presentation_product",
    "ck_global_product_identifiers_type",
    "ck_global_product_identifiers_gtin_format",
    "ck_global_product_identifiers_value_normalized",
    "ck_global_product_identifiers_primary_active",
    "ck_global_product_identifiers_ium_format",
    "uq_global_product_group_types_code",
    "ck_global_product_group_types_display_order",
    "uq_global_product_groups_type_code",
    "uq_global_product_groups_id_type",
    "fk_global_product_groups_parent_same_type",
    "ck_global_product_groups_not_self_parent",
    "uq_global_product_group_assignments_product_group",
    "fk_global_product_group_assignments_group_type",
    "ck_product_assets_asset_type",
    "ck_product_assets_primary_active",
}

EXPECTED_INDEXES = {
    "ix_global_categories_parent_category_id",
    "ix_global_products_canonical_name_key_trgm",
    "ix_global_products_duplicate_key",
    "ix_global_products_manufacturer_organization_id",
    "ix_global_products_global_brand_id",
    "ix_global_products_base_unit_id",
    "ix_global_products_status",
    "uq_global_product_categories_primary",
    "uq_global_product_presentations_base",
    "uq_global_product_identifiers_gtin_family",
    "uq_global_product_identifiers_barcode",
    "uq_global_product_identifiers_other",
    "uq_global_product_identifiers_ium",
    "uq_global_product_identifiers_primary",
    "ix_global_product_group_assignments_product_type",
    "uq_product_assets_primary",
    "ix_global_product_identifiers_global_product_id",
    "ix_global_product_group_assignments_global_product_id",
}


def test_all_tables_exist(test_engine: Engine) -> None:
    tables = set(inspect(test_engine).get_table_names())
    assert set(FUNCTIONAL_TABLES) <= tables


def test_pg_trgm_extension_exists(test_engine: Engine) -> None:
    with test_engine.connect() as connection:
        assert connection.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
        ).scalar_one() == 1


def test_named_constraints_exist(test_engine: Engine) -> None:
    with test_engine.connect() as connection:
        names = set(connection.execute(text("SELECT conname FROM pg_constraint")).scalars())
    missing = EXPECTED_CONSTRAINTS - names
    assert not missing, missing


def test_named_indexes_exist(test_engine: Engine) -> None:
    with test_engine.connect() as connection:
        names = set(connection.execute(text("SELECT indexname FROM pg_indexes")).scalars())
    missing = EXPECTED_INDEXES - names
    assert not missing, missing


def test_identifier_primary_index_is_nulls_not_distinct(test_engine: Engine) -> None:
    with test_engine.connect() as connection:
        definition = connection.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'uq_global_product_identifiers_primary'"
            )
        ).scalar_one()
    assert "NULLS NOT DISTINCT" in definition


def test_downgrade_and_upgrade_from_scratch(test_database_url: str, test_engine: Engine) -> None:
    config = build_alembic_config()
    command.downgrade(config, "base")

    engine = create_engine(test_database_url)
    try:
        remaining = set(inspect(engine).get_table_names()) & set(FUNCTIONAL_TABLES)
        assert not remaining
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    assert set(FUNCTIONAL_TABLES) <= set(inspect(test_engine).get_table_names())


def test_filter_indexes_migration_downgrades_and_upgrades(test_database_url: str) -> None:
    """La migración 0002 crea y elimina solo sus dos índices."""
    new_indexes = {
        "ix_global_product_identifiers_global_product_id",
        "ix_global_product_group_assignments_global_product_id",
    }
    config = build_alembic_config()
    engine = create_engine(test_database_url)

    def indexes() -> set[str]:
        with engine.connect() as connection:
            return set(connection.execute(text("SELECT indexname FROM pg_indexes")).scalars())

    try:
        command.downgrade(config, "0001")
        assert not (new_indexes & indexes())
        assert set(FUNCTIONAL_TABLES) - {"audit_outbox"} <= set(inspect(engine).get_table_names())  # la outbox llega en 0003

        command.upgrade(config, "head")
        assert new_indexes <= indexes()
    finally:
        engine.dispose()


def test_ium_migration_downgrades_and_upgrades(test_database_url: str) -> None:
    """La migración 0004 agrega y retira solo el tipo IUM (spec 018, RC-IUM-5)."""
    config = build_alembic_config()
    engine = create_engine(test_database_url)

    def ium_objects() -> set[str]:
        with engine.connect() as connection:
            names = set(connection.execute(text("SELECT indexname FROM pg_indexes")).scalars())
            names |= set(connection.execute(text("SELECT conname FROM pg_constraint")).scalars())
            type_check = connection.execute(
                text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_global_product_identifiers_type'")
            ).scalar_one()
        return {name for name in names if "ium" in name} | ({"IUM en el CHECK de tipos"} if "IUM" in type_check else set())

    expected = {"uq_global_product_identifiers_ium", "ck_global_product_identifiers_ium_format", "IUM en el CHECK de tipos"}
    try:
        command.downgrade(config, "0003")
        assert not ium_objects()
        command.upgrade(config, "head")
        assert ium_objects() == expected
    finally:
        engine.dispose()


def test_ium_migration_downgrade_refuses_existing_ium_rows(test_database_url: str, session_factory) -> None:
    """Con identificadores IUM, la reversión falla sin borrar datos (spec 018, plan: impacto)."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    from tests import factories

    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, "Con IUM")
    box = factories.presentation(session_factory, product.id, "CAJA")
    factories.identifier(session_factory, product.id, "2H1005971005105", "IUM", presentation_id=box.id)
    config = build_alembic_config()
    engine = create_engine(test_database_url)
    try:
        with pytest.raises(IntegrityError, match="ck_global_product_identifiers_type"):
            command.downgrade(config, "0003")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0004"
            assert connection.execute(
                text("SELECT count(*) FROM global_product_identifiers WHERE identifier_type = 'IUM'")
            ).scalar_one() == 1
    finally:
        engine.dispose()
