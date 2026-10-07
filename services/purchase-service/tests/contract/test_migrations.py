"""Migración `0001` (data-model.md; T010)."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from tests.conftest import run_alembic

TABLES = {
    "purchases",
    "purchase_details",
    "purchase_sequences",
    "purchase_sequence_counters",
    "purchase_operations",
    "purchase_lifecycle_events",
    "audit_outbox",
}
TRIGGERS = {
    "tr_purchases_frozen",
    "tr_purchases_no_delete",
    "tr_purchases_no_truncate",
    "tr_purchase_details_draft_only",
    "tr_purchase_sequences_no_delete",
    "tr_purchase_sequence_counters_monotonic",
    "tr_purchase_sequence_counters_no_delete",
    "tr_purchase_operations_terminal",
    "tr_purchase_operations_no_delete",
    "tr_purchase_lifecycle_events_no_update",
    "tr_purchase_lifecycle_events_no_delete",
    "tr_purchase_lifecycle_events_no_truncate",
}
UNIQUE_INDEXES = {
    "uq_purchases_company_number",
    "uq_purchase_sequences_active",
    "uq_purchase_sequences_series",
    "uq_purchase_operations_pending",
}
CHECKS = {
    "ck_purchases_lifecycle",
    "ck_purchases_status",
    "ck_purchases_totals",
    "ck_purchases_due_date",
    "ck_purchases_payment_terms",
    "ck_purchases_payment_code",
    "ck_purchases_currency_code",
    "ck_purchase_details_line_number",
    "ck_purchase_details_discount_amount",
    "ck_purchase_details_presentation",
    "ck_purchase_details_total",
    "ck_purchase_sequences_document_kind",
    "ck_purchase_sequences_number_text_length",
    "ck_purchase_sequence_counters_period_key",
    "ck_purchase_operations_failed_code",
    "ck_purchase_operations_completed_at",
    "ck_purchase_operations_inventory_operation",
    "ck_purchase_lifecycle_events_event_type",
}


def test_upgrade_downgrade_upgrade(test_database_url, clean_database) -> None:
    run_alembic(test_database_url, "downgrade", "base")
    engine = create_engine(test_database_url)
    try:
        assert not TABLES & set(inspect(engine).get_table_names())
        run_alembic(test_database_url, "upgrade", "head")
        inspector = inspect(engine)
        assert TABLES <= set(inspector.get_table_names())

        columns = {column["name"] for column in inspector.get_columns("purchase_sequences")}
        assert "current_number" not in columns and "last_reset_at" not in columns  # BR-14, P-04
        operation_columns = {column["name"] for column in inspector.get_columns("purchase_operations")}
        assert {"created_at", "created_by", "updated_at", "updated_by", "inventory_operation_id",
                "application_user_id", "reason"} <= operation_columns  # P-05, D-02, D-07
        assert "inventory_operation_id" in {column["name"] for column in inspector.get_columns("purchases")}

        with engine.connect() as connection:
            triggers = set(connection.execute(text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")).scalars())
            indexes = set(
                connection.execute(
                    text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexdef LIKE 'CREATE UNIQUE%'")
                ).scalars()
            )
            checks = set(connection.execute(text("SELECT conname FROM pg_constraint WHERE contype = 'c'")).scalars())
        assert TRIGGERS <= triggers
        assert UNIQUE_INDEXES <= indexes
        assert CHECKS <= checks
    finally:
        engine.dispose()
