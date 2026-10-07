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


# Fase B (013): migración `0002` (T006) -------------------------------------------

TABLES_013 = {
    "company_inventory_policies",
    "inventory_policies",
    "inventory_adjustments",
    "inventory_counts",
    "inventory_count_details",
    "inventory_cost_layers",
    "inventory_cost_consumptions",
}

CONSTRAINTS_013 = {
    "inventory_balances": {"ck_inventory_balances_inventory_value_non_negative"},
    "inventory_movements": {"ck_inventory_movements_movement_value_non_negative", "ck_inventory_movements_valued"},
    "company_inventory_policies": {
        "pk_company_inventory_policies",
        "uq_company_inventory_policies_company",
        "ck_company_inventory_policies_system",
        "ck_company_inventory_policies_valuation_fifo",
        "ck_company_inventory_policies_replenishment",
    },
    "inventory_policies": {
        "pk_inventory_policies",
        "ck_inventory_policies_levels",
        "ck_inventory_policies_service_level",
        "ck_inventory_policies_window",
        "ck_inventory_policies_safety_method",
        "ck_inventory_policies_mode",
    },
    "inventory_adjustments": {
        "pk_inventory_adjustments",
        "fk_inventory_adjustments_operation",
        "fk_inventory_adjustments_movement",
        "uq_inventory_adjustments_movement",
        "fk_inventory_adjustments_count",
        "ck_inventory_adjustments_type",
        "ck_inventory_adjustments_quantity_positive",
        "ck_inventory_adjustments_reason",
        "ck_inventory_adjustments_balance_math",
        "ck_inventory_adjustments_values_non_negative",
        "ck_inventory_adjustments_audit_unchanged",
    },
    "inventory_counts": {
        "pk_inventory_counts",
        "fk_inventory_counts_operation",
        "ck_inventory_counts_status",
        "ck_inventory_counts_lifecycle",
    },
    "inventory_count_details": {
        "pk_inventory_count_details",
        "fk_inventory_count_details_count",
        "fk_inventory_count_details_adjustment",
        "uq_inventory_count_details_product",
        "ck_inventory_count_details_quantities",
        "ck_inventory_count_details_difference",
    },
    "inventory_cost_layers": {
        "pk_inventory_cost_layers",
        "fk_inventory_cost_layers_origin_movement",
        "uq_inventory_cost_layers_origin_movement",
        "ck_inventory_cost_layers_kind",
        "ck_inventory_cost_layers_origin",
        "ck_inventory_cost_layers_quantities",
        "ck_inventory_cost_layers_status_matches_remaining",
        "ck_inventory_cost_layers_unit_cost",
        "ck_inventory_cost_layers_currency",
        "ck_inventory_cost_layers_cost_known",
    },
    "inventory_cost_consumptions": {
        "pk_inventory_cost_consumptions",
        "fk_inventory_cost_consumptions_movement",
        "fk_inventory_cost_consumptions_layer",
        "fk_inventory_cost_consumptions_restores",
        "uq_inventory_cost_consumptions_restores",
        "ck_inventory_cost_consumptions_type",
        "ck_inventory_cost_consumptions_quantity_positive",
        "ck_inventory_cost_consumptions_restore_link",
    },
}

INDEXES_013 = {
    "ix_inventory_cost_layers_open",
    "uq_inventory_cost_layers_opening",
    "uq_inventory_policies_active",
    "uq_inventory_counts_in_progress",
    "ix_inventory_cost_consumptions_movement",
    "ix_inventory_cost_consumptions_layer",
}

TRIGGERS_013 = {
    "tr_inventory_adjustments_no_update",
    "tr_inventory_adjustments_no_delete",
    "tr_inventory_adjustments_no_truncate",
    "tr_inventory_cost_consumptions_no_update",
    "tr_inventory_cost_consumptions_no_delete",
    "tr_inventory_cost_consumptions_no_truncate",
    "tr_inventory_cost_layers_no_delete",
    "tr_inventory_cost_layers_no_truncate",
    "tr_inventory_count_details_finalized",
}


def test_0002_round_trip_to_0001_and_back(scratch_url) -> None:
    run_alembic(scratch_url, "upgrade", "head")
    engine = create_engine(scratch_url)
    try:
        assert TABLES | TABLES_013 <= set(inspect(engine).get_table_names(schema="migration_check"))

        run_alembic(scratch_url, "downgrade", "0001")
        names = set(inspect(engine).get_table_names(schema="migration_check"))
        assert TABLES <= names
        assert not names & TABLES_013
        with engine.connect() as connection:
            columns = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'migration_check' AND table_name IN ('inventory_movements','inventory_balances')"
                    )
                )
            }
        assert not columns & {"movement_value", "cost_known", "inventory_value", "average_unit_cost", "has_unknown_cost"}

        run_alembic(scratch_url, "upgrade", "head")
        assert TABLES_013 <= set(inspect(engine).get_table_names(schema="migration_check"))
    finally:
        engine.dispose()


def test_0002_named_constraints_indexes_and_triggers(test_engine) -> None:
    with test_engine.connect() as connection:
        assert TABLES_013 <= set(inspect(connection).get_table_names())
        for table, expected in CONSTRAINTS_013.items():
            assert expected <= _constraint_names(connection, table), table

        indexes = {row[0] for row in connection.execute(text("SELECT indexname FROM pg_indexes"))}
        assert INDEXES_013 <= indexes

        triggers = {row[0] for row in connection.execute(text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal"))}
        assert TRIGGERS_013 <= triggers


def test_valued_movement_check_is_not_valid_only_for_history(test_engine) -> None:
    """`NOT VALID`: no revalida el historial de la Fase A, pero aplica a toda fila nueva (punto 6)."""
    with test_engine.connect() as connection:
        convalidated = connection.execute(
            text("SELECT convalidated FROM pg_constraint WHERE conname = 'ck_inventory_movements_valued'")
        ).scalar_one()
    assert convalidated is False
