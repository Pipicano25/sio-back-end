"""Migración `0001` (data-model.md; T012)."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from tests.conftest import run_alembic

TABLES = {
    "sales",
    "sale_details",
    "sale_sequences",
    "sale_sequence_counters",
    "sale_operations",
    "audit_outbox",
}
TRIGGERS = {
    "tr_sales_frozen",
    "tr_sales_no_delete",
    "tr_sales_no_truncate",
    "tr_sale_details_draft_only",
    "tr_sale_sequences_no_delete",
    "tr_sale_sequence_counters_monotonic",
    "tr_sale_sequence_counters_no_delete",
    "tr_sale_operations_terminal",
    "tr_sale_operations_no_delete",
}
UNIQUE_INDEXES = {
    "uq_sales_company_number",
    "uq_sale_sequences_active",
    "uq_sale_sequences_series",
    "uq_sale_operations_pending",
}
CHECKS = {
    "ck_sales_payment_method_required",  # spec 020
    "ck_sale_details_no_discount",  # spec 020
    "ck_sales_lifecycle",
    "ck_sales_status",
    "ck_sales_totals",
    "ck_sales_cash_only",
    "ck_sales_draft_unknown_cost",
    "ck_sales_payment_terms",
    "ck_sales_payment_code",
    "ck_sales_currency_code",
    "ck_sale_details_line_number",
    "ck_sale_details_discount_amount",
    "ck_sale_details_presentation",
    "ck_sale_details_total",
    "ck_sale_details_unit_price",
    "ck_sale_details_cost_block",
    "ck_sale_details_margin_amount",
    "ck_sale_details_margin_percentage",
    "ck_sale_details_price_list_item",
    "ck_sale_details_price_list_requested",
    "ck_sale_sequences_document_kind",
    "ck_sale_sequences_number_text_length",
    "ck_sale_sequence_counters_period_key",
    "ck_sale_operations_failed_code",
    "ck_sale_operations_completed_at",
    "ck_sale_operations_inventory_operation",
    "ck_sale_operations_cancel_reason",
}


def test_upgrade_downgrade_upgrade(test_database_url, clean_database) -> None:
    run_alembic(test_database_url, "downgrade", "base")
    engine = create_engine(test_database_url)
    try:
        assert not TABLES & set(inspect(engine).get_table_names())
        run_alembic(test_database_url, "upgrade", "head")
        inspector = inspect(engine)
        assert TABLES <= set(inspector.get_table_names())

        columns = {column["name"] for column in inspector.get_columns("sale_sequences")}
        assert "current_number" not in columns and "last_reset_at" not in columns  # BR-15, C-05
        operation_columns = {column["name"] for column in inspector.get_columns("sale_operations")}
        assert {"created_at", "created_by", "updated_at", "updated_by", "inventory_operation_id",
                "application_user_id", "reason"} <= operation_columns  # BR-15, C-07
        sale_columns = {column["name"] for column in inspector.get_columns("sales")}
        assert {"inventory_operation_id", "has_unknown_cost", "company_customer_id",
                "customer_payment_condition_id", "created_by", "updated_by"} <= sale_columns  # C-03, C-04, C-07
        detail_columns = {column["name"]: column for column in inspector.get_columns("sale_details")}
        assert {"price_list_id", "price_list_item_id", "price_list_requested", "unit_price",
                "unit_cost_snapshot", "cost_total", "cost_known", "gross_margin_amount",
                "gross_margin_percentage"} <= set(detail_columns)  # §8.2, P-02, C-03
        assert (detail_columns["unit_price"]["type"].precision, detail_columns["unit_price"]["type"].scale) == (18, 4)
        percentage = detail_columns["gross_margin_percentage"]["type"]
        assert (percentage.precision, percentage.scale) == (7, 4)  # P-01

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
