"""Migraciones desde cero y reversibles (FR-074, RC-13, DS-06; puerta de calidad 3)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine, inspect, text

from tests.conftest import run_alembic

TABLES = ("company_products", "company_customers", "company_suppliers")
SPEC_021_TABLES = (
    "price_list_pricing_policies",
    "price_list_pricing_policy_terms",
    "price_list_pricing_policy_presentations",
    "automatic_price_update_requests",
    "automatic_price_applications",
)

EXPECTED_CONSTRAINTS = {
    "company_products": {
        "pk_company_products",
        "uq_company_products_company_id_global_product_id",
        "ck_company_products_status",
        "ck_company_products_currency_code_format",
        "ck_company_products_lot_requires_inventory",
        "ck_company_products_expiration_requires_lot",
        "ck_company_products_internal_code_not_blank",
        "ck_company_products_display_name_not_blank",
    },
    "company_customers": {
        "pk_company_customers",
        "ck_company_customers_kind",
        "ck_company_customers_identity_by_kind",
        "ck_company_customers_contact_only_organization",
        "ck_company_customers_status",
        "ck_company_customers_internal_code_not_blank",
        "ck_company_customers_display_name_not_blank",
    },
    "company_suppliers": {
        "pk_company_suppliers",
        "uq_company_suppliers_company_id_organization_identity_id",
        "ck_company_suppliers_status",
        "ck_company_suppliers_block_reason_consistency",
        "ck_company_suppliers_internal_code_not_blank",
        "ck_company_suppliers_display_name_not_blank",
    },
}

EXPECTED_INDEXES = {
    "company_products": {
        "uq_company_products_company_id_internal_code_ci",
        "ix_company_products_company_id_status",
        "ix_company_products_global_product_id",
    },
    "company_customers": {
        "uq_company_customers_company_id_person_identity_id",
        "uq_company_customers_company_id_organization_identity_id",
        "uq_company_customers_company_id_internal_code_ci",
        "ix_company_customers_company_id_status",
        "ix_company_customers_person_identity_id",
        "ix_company_customers_organization_identity_id",
    },
    "company_suppliers": {
        "uq_company_suppliers_company_id_internal_code_ci",
        "ix_company_suppliers_company_id_status",
        "ix_company_suppliers_organization_identity_id",
    },
}

# Datos de otros servicios que NO deben existir como columnas (Principio III, RC-13).
FORBIDDEN_COLUMNS = {
    "canonical_name",
    "legal_name",
    "first_name",
    "last_name",
    "identification_number",
    "email",
    "phone",
    "address",
    "global_brand_id",
    "base_unit_id",
    "customer_segment_id",
    "created_by_user_id",
    "is_active",
    "relationship_status",
}


def _constraint_names(connection, table: str) -> set[str]:
    rows = connection.execute(
        text("SELECT conname FROM pg_constraint WHERE conrelid = CAST(:table AS regclass)"),
        {"table": table},
    )
    return {row[0] for row in rows}


def _index_names(connection, table: str) -> set[str]:
    rows = connection.execute(
        text("SELECT indexname FROM pg_indexes WHERE tablename = :table"), {"table": table}
    )
    return {row[0] for row in rows}


def test_upgrade_creates_tables_constraints_and_indexes(test_database_url, migrated_database):
    engine = create_engine(test_database_url)

    try:
        with engine.connect() as connection:
            for table in TABLES:
                assert EXPECTED_CONSTRAINTS[table] <= _constraint_names(connection, table), table
                assert EXPECTED_INDEXES[table] <= _index_names(connection, table), table

            foreign_keys = connection.execute(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE contype = 'f' "
                    "AND conrelid::regclass::text = ANY(:tables)"
                ),
                {"tables": list(TABLES)},
            ).scalar()
            assert foreign_keys == 0  # sin FK físicas (Principio II)

        columns = {
            column["name"]
            for table in TABLES
            for column in inspect(engine).get_columns(table)
        }
        assert not columns & FORBIDDEN_COLUMNS
        assert {"created_by", "updated_by", "version", "status", "block_reason"} <= columns
    finally:
        engine.dispose()


def test_downgrade_and_upgrade_again(test_database_url, migrated_database):
    run_alembic(test_database_url, "downgrade", "base")
    engine = create_engine(test_database_url)

    try:
        assert not set(TABLES) & set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    run_alembic(test_database_url, "upgrade", "head")
    engine = create_engine(test_database_url)

    try:
        assert set(TABLES) <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


# --------------------------------------------------------------------------
# Fase B (specs/010-commercial-relationship-commercial-product, T003, R-15)
# --------------------------------------------------------------------------

PHASE_B_TABLES = (
    "company_product_presentations",
    "supplier_products",
    "supplier_payment_conditions",
    "price_lists",
    "price_list_items",
)

PHASE_B_CONSTRAINTS = {
    "company_products": {"uq_company_products_id_company_id"},
    "company_suppliers": {"uq_company_suppliers_id_company_id"},
    "company_product_presentations": {
        "pk_company_product_presentations",
        "fk_company_product_presentations_company_product",
        "uq_company_product_presentations_id_company_id",
        "uq_company_product_presentations_id_company_product_id",
        "uq_company_product_presentations_product_global_presentation",
        "ck_company_product_presentations_status",
        "ck_company_product_presentations_default_purchase_purchasable",
        "ck_company_product_presentations_default_sale_sellable",
        "ck_company_product_presentations_default_requires_active",
        "ck_company_product_presentations_codes_not_blank",
    },
    "supplier_products": {
        "pk_supplier_products",
        "fk_supplier_products_company_supplier",
        "fk_supplier_products_company_product",
        "fk_supplier_products_presentation",
        "ck_supplier_products_status",
        "ck_supplier_products_currency_code_format",
        "ck_supplier_products_quantities",
        "ck_supplier_products_non_negative",
        "ck_supplier_products_preferred_requires_active",
    },
    "supplier_payment_conditions": {
        "pk_supplier_payment_conditions",
        "fk_supplier_payment_conditions_company_supplier",
        "ck_supplier_payment_conditions_status",
        "ck_supplier_payment_conditions_currency_code_format",
        "ck_supplier_payment_conditions_terms_range",
        "ck_supplier_payment_conditions_amounts",
        "ck_supplier_payment_conditions_validity",
        "ck_supplier_payment_conditions_default_requires_active",
    },
    "price_lists": {
        "pk_price_lists",
        "uq_price_lists_id_company_id",
        "ck_price_lists_status",
        "ck_price_lists_currency_code_format",
        "ck_price_lists_validity",
        "ck_price_lists_default_requires_active",
        "ck_price_lists_code_not_blank",
        "ck_price_lists_name_not_blank",
    },
    "price_list_items": {
        "pk_price_list_items",
        "fk_price_list_items_price_list",
        "fk_price_list_items_company_product",
        "fk_price_list_items_presentation",
        "ex_price_list_items_no_overlap",
        "ck_price_list_items_status",
        "ck_price_list_items_unit_price_non_negative",
        "ck_price_list_items_validity",
    },
}

PHASE_B_INDEXES = {
    "company_product_presentations": {
        "uq_company_product_presentations_company_id_sku_ci",
        "uq_company_product_presentations_company_id_internal_code_ci",
        "uq_company_product_presentations_default_purchase",
        "uq_company_product_presentations_default_sale",
        "ix_company_product_presentations_company_id_status",
        "ix_company_product_presentations_global_product_presentation_id",
    },
    "supplier_products": {
        "uq_supplier_products_active_relation",
        "uq_supplier_products_preferred",
        "ix_supplier_products_company_id_status",
        "ix_supplier_products_company_product_id",
        "ix_supplier_products_company_supplier_id",
    },
    "supplier_payment_conditions": {
        "uq_supplier_payment_conditions_default",
        "ix_supplier_payment_conditions_company_supplier_id",
        "ix_supplier_payment_conditions_payment_condition_type_id",
    },
    "price_lists": {
        "uq_price_lists_company_id_code_ci",
        "uq_price_lists_default",
        "ix_price_lists_company_id_status",
    },
    "price_list_items": {
        "ix_price_list_items_resolution",
        "ix_price_list_items_company_id_status",
    },
}


def test_phase_b_upgrade_creates_tables_constraints_indexes_and_extension(test_database_url, migrated_database):
    engine = create_engine(test_database_url)

    try:
        with engine.connect() as connection:
            for table, expected in PHASE_B_CONSTRAINTS.items():
                assert expected <= _constraint_names(connection, table), table

            for table, expected in PHASE_B_INDEXES.items():
                assert expected <= _index_names(connection, table), table

            assert connection.execute(
                text("SELECT count(*) FROM pg_extension WHERE extname = 'btree_gist'")
            ).scalar() == 1

            # Las FK de la Fase B son solo internas (misma base, Principio II).
            referenced = connection.execute(
                text(
                    "SELECT DISTINCT confrelid::regclass::text FROM pg_constraint "
                    "WHERE contype = 'f' AND conrelid::regclass::text = ANY(:tables)"
                ),
                {"tables": list(PHASE_B_TABLES)},
            ).scalars().all()
            # Spec 021: `price_list_items.automatic_application_id` → `automatic_price_applications` (interna).
            assert set(referenced) <= set(TABLES) | set(PHASE_B_TABLES) | set(SPEC_021_TABLES)
    finally:
        engine.dispose()


def test_phase_b_applies_over_phase_a_data_and_reverts(test_database_url, migrated_database):
    """FR-094: `0002` aplica sobre una base en `0001` con filas y revierte sin tocarlas."""
    run_alembic(test_database_url, "downgrade", "0001")
    engine = create_engine(test_database_url)
    product_id, supplier_id, company_id = uuid4(), uuid4(), uuid4()

    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE company_products, company_suppliers"))
            connection.execute(
                text(
                    "INSERT INTO company_products (id, company_id, global_product_id, internal_code, "
                    "display_name, currency_code, created_by, updated_by) "
                    "VALUES (:id, :company, :global, 'P-1', 'Producto', 'COP', 'sub', 'sub')"
                ),
                {"id": product_id, "company": company_id, "global": uuid4()},
            )
            connection.execute(
                text(
                    "INSERT INTO company_suppliers (id, company_id, organization_identity_id, "
                    "internal_code, display_name, created_by, updated_by) "
                    "VALUES (:id, :company, :org, 'S-1', 'Proveedor', 'sub', 'sub')"
                ),
                {"id": supplier_id, "company": company_id, "org": uuid4()},
            )

        run_alembic(test_database_url, "upgrade", "head")
        assert set(PHASE_B_TABLES) <= set(inspect(engine).get_table_names())

        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM company_products")).scalar() == 1
            assert connection.execute(text("SELECT count(*) FROM company_suppliers")).scalar() == 1

        run_alembic(test_database_url, "downgrade", "0001")
        engine.dispose()
        assert not set(PHASE_B_TABLES) & set(inspect(engine).get_table_names())

        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM company_products")).scalar() == 1
            assert "uq_company_products_id_company_id" not in _constraint_names(
                connection, "company_products"
            )
    finally:
        engine.dispose()
        run_alembic(test_database_url, "upgrade", "head")
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE company_products, company_suppliers CASCADE"))
        engine.dispose()


# --------------------------------------------------------------------------
# Spec 019 (0004): sin precio ni costo en company_products, con guarda contra pérdida de valores
# --------------------------------------------------------------------------


def _insert_legacy_product(connection, sale_price: str, reference_cost: str):
    product_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO company_products (id, company_id, global_product_id, internal_code, display_name, currency_code, "
            "sale_price, reference_cost, status, version, created_by, updated_by, created_at, updated_at) VALUES "
            "(:id, :company, :product, 'LEG-1', 'Producto legado', 'COP', :price, :cost, 'ACTIVE', 1, 'sub', 'sub', now(), now())"
        ),
        {"id": product_id, "company": uuid4(), "product": uuid4(), "price": sale_price, "cost": reference_cost},
    )
    return product_id


def _columns(engine) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("company_products")}


def test_0004_removes_price_and_cost_columns(test_database_url, migrated_database):
    engine = create_engine(test_database_url)
    try:
        assert not {"sale_price", "reference_cost"} & _columns(engine)
        assert "currency_code" in _columns(engine)  # se conserva (elige la lista predeterminada)
    finally:
        engine.dispose()


def test_0004_keeps_rows_with_default_zeros(test_database_url, migrated_database):
    run_alembic(test_database_url, "downgrade", "0003")
    engine = create_engine(test_database_url)
    try:
        with engine.begin() as connection:
            product_id = _insert_legacy_product(connection, "0", "0")
        run_alembic(test_database_url, "upgrade", "head")
        with engine.begin() as connection:
            assert connection.execute(text("SELECT count(*) FROM company_products WHERE id = :id"), {"id": product_id}).scalar_one() == 1
            connection.execute(text("DELETE FROM company_products"))
    finally:
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()


def test_0004_guard_refuses_to_lose_commercial_values(test_database_url, migrated_database):
    """RC-PRC-5: con un precio o costo distinto de 0, la migración se detiene sin cambios."""
    import pytest

    run_alembic(test_database_url, "downgrade", "0003")
    engine = create_engine(test_database_url)
    try:
        with engine.begin() as connection:
            _insert_legacy_product(connection, "1500.00", "0")
        with pytest.raises(RuntimeError, match="eliminaría precios o costos de 1"):
            run_alembic(test_database_url, "upgrade", "head")
        assert {"sale_price", "reference_cost"} <= _columns(engine)  # nada cambió
        with engine.begin() as connection:
            assert connection.execute(text("SELECT sale_price FROM company_products")).scalar_one() == 1500
            connection.execute(text("DELETE FROM company_products"))  # dato sintético de la prueba
    finally:
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()
