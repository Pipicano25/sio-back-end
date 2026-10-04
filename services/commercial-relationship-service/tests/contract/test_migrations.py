"""Migraciones desde cero y reversibles (FR-074, RC-13, DS-06; puerta de calidad 3)."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from tests.conftest import run_alembic

TABLES = ("company_products", "company_customers", "company_suppliers")

EXPECTED_CONSTRAINTS = {
    "company_products": {
        "pk_company_products",
        "uq_company_products_company_id_global_product_id",
        "ck_company_products_status",
        "ck_company_products_sale_price_non_negative",
        "ck_company_products_reference_cost_non_negative",
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
