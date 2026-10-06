"""Migración `0001` desde cero, ida y vuelta (Principio VIII, puerta 3; T009)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text

from tests.conftest import run_alembic

TABLES = {"inventory_operations", "inventory_balances", "inventory_movements", "audit_outbox"}

CONSTRAINTS = {
    "inventory_operations": {
        "pk_inventory_operations",
        "uq_inventory_operations_operation_key",
        "uq_inventory_operations_reverses",
        "fk_inventory_operations_reverses",
        "ck_inventory_operations_type",
        "ck_inventory_operations_origin_type",
        "ck_inventory_operations_reversal_link",
        "ck_inventory_operations_reason",
        "ck_inventory_operations_line_count",
        "ck_inventory_operations_request_hash_format",
    },
    "inventory_balances": {
        "pk_inventory_balances",
        "uq_inventory_balances_product",
        "ck_inventory_balances_quantity_non_negative",
        "ck_inventory_balances_version_non_negative",
    },
    "inventory_movements": {
        "pk_inventory_movements",
        "fk_inventory_movements_operation",
        "fk_inventory_movements_reversed",
        "uq_inventory_movements_sequence",
        "uq_inventory_movements_operation_line",
        "uq_inventory_movements_reversed",
        "ck_inventory_movements_type",
        "ck_inventory_movements_quantity_positive",
        "ck_inventory_movements_balances_non_negative",
        "ck_inventory_movements_balance_math",
        "ck_inventory_movements_unit_cost",
        "ck_inventory_movements_reversal_link",
        "ck_inventory_movements_audit_unchanged",
    },
}

INDEXES = {"ix_inventory_balances_in_stock", "ix_inventory_movements_origin", "ix_inventory_operations_company"}

TRIGGERS = {
    "tr_inventory_movements_no_update",
    "tr_inventory_movements_no_delete",
    "tr_inventory_movements_no_truncate",
    "tr_inventory_operations_no_update",
    "tr_inventory_operations_no_delete",
    "tr_inventory_operations_no_truncate",
    "tr_inventory_balances_no_delete",
    "tr_inventory_balances_no_truncate",
}


def _constraint_names(connection, table: str) -> set[str]:
    rows = connection.execute(
        text("SELECT conname FROM pg_constraint WHERE conrelid = CAST(:table AS regclass)"),
        {"table": table},
    )
    return {row[0] for row in rows}


@pytest.fixture
def scratch_url(test_database_url):
    """Esquema vacío temporal en la base de pruebas para la ida y vuelta."""
    engine = create_engine(test_database_url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS migration_check CASCADE"))
        connection.execute(text("CREATE SCHEMA migration_check"))
    engine.dispose()
    separator = "&" if "?" in test_database_url else "?"
    url = f"{test_database_url}{separator}options=-csearch_path%3Dmigration_check"
    yield url
    engine = create_engine(test_database_url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS migration_check CASCADE"))
    engine.dispose()


def test_upgrade_downgrade_upgrade_from_empty(scratch_url) -> None:
    run_alembic(scratch_url, "upgrade", "head")
    engine = create_engine(scratch_url)
    try:
        assert TABLES <= set(inspect(engine).get_table_names(schema="migration_check"))

        run_alembic(scratch_url, "downgrade", "base")
        assert set(inspect(engine).get_table_names(schema="migration_check")) == {"alembic_version"}

        run_alembic(scratch_url, "upgrade", "head")
        assert TABLES <= set(inspect(engine).get_table_names(schema="migration_check"))
    finally:
        engine.dispose()


def test_named_constraints_indexes_function_and_triggers(test_engine) -> None:
    with test_engine.connect() as connection:
        for table, expected in CONSTRAINTS.items():
            assert expected <= _constraint_names(connection, table), table

        indexes = {row[0] for row in connection.execute(text("SELECT indexname FROM pg_indexes"))}
        assert INDEXES <= indexes

        functions = {row[0] for row in connection.execute(text("SELECT proname FROM pg_proc"))}
        assert "inventory_reject_change" in functions

        triggers = {row[0] for row in connection.execute(text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal"))}
        assert TRIGGERS <= triggers


def test_balance_sequence_is_not_backed_by_a_postgres_sequence(test_engine) -> None:
    """R-04: el correlativo del kardex nunca sale de una SEQUENCE (dejaría huecos)."""
    with test_engine.connect() as connection:
        default = connection.execute(
            text(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = 'inventory_movements' AND column_name = 'balance_sequence'"
            )
        ).scalar_one()
        owned = connection.execute(
            text(
                "SELECT count(*) FROM pg_class s JOIN pg_depend d ON d.objid = s.oid "
                "WHERE s.relkind = 'S' AND d.refobjid IN (CAST('inventory_movements' AS regclass), "
                "CAST('inventory_balances' AS regclass), CAST('inventory_operations' AS regclass))"
            )
        ).scalar_one()
    assert default is None
    assert owned == 0
