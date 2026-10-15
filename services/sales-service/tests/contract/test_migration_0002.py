"""Migración `0002` (spec 020): medio de pago, ventas sin descuento, trigger reemplazado y guardas (DS-09)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text

from tests.conftest import run_alembic
from tests.contract.db_rows import insert_detail

NEW_COLUMNS = {"payment_method_id", "payment_method_code_snapshot", "payment_method_name_snapshot"}
NEW_CHECKS = {"ck_sales_payment_method_snapshot", "ck_sales_payment_method_required", "ck_sale_details_no_discount"}


def checks(engine) -> set[str]:
    with engine.connect() as connection:
        return set(connection.execute(text("SELECT conname FROM pg_constraint WHERE contype = 'c'")).scalars())


def test_upgrade_adds_rules_and_downgrade_restores_0001(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        assert NEW_COLUMNS <= {column["name"] for column in inspect(engine).get_columns("sales")}
        assert NEW_CHECKS <= checks(engine)
        run_alembic(test_database_url, "downgrade", "0001")
        assert not NEW_COLUMNS & {column["name"] for column in inspect(engine).get_columns("sales")}
        assert not NEW_CHECKS & checks(engine)
    finally:
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()


def test_guard_stops_without_changes_when_a_discount_exists(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        run_alembic(test_database_url, "downgrade", "0001")
        with engine.begin() as connection:
            sale = uuid4()
            connection.execute(
                text(
                    "INSERT INTO sales (id, company_id, branch_id, company_customer_id, payment_condition_code_snapshot, "
                    "payment_terms_days_snapshot, due_date, status, operation_date, customer_name_snapshot, "
                    "customer_identification_snapshot, currency_code, created_by_user_id, created_by, updated_by) "
                    "VALUES (:id, :c, :b, :cu, 'CASH', 0, DATE '2026-10-14', 'DRAFT', DATE '2026-10-14', 'Cliente', 'CC 1', "
                    "'COP', :u, 'sub', 'sub')"
                ),
                {"id": sale, "c": uuid4(), "b": uuid4(), "cu": uuid4(), "u": uuid4()},
            )
            insert_detail(connection, sale, discount_amount=1, total=9)
        with pytest.raises(RuntimeError, match="con descuento"):
            run_alembic(test_database_url, "upgrade", "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001"
    finally:
        with engine.begin() as connection:
            for table, triggers in (
                ("sale_details", ("tr_sale_details_draft_only",)),
                ("sales", ("tr_sales_no_delete",)),
            ):
                for trigger in triggers:
                    connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))
            connection.execute(text("DELETE FROM sale_details"))
            connection.execute(text("DELETE FROM sales"))
            for table, triggers in (("sale_details", ("tr_sale_details_draft_only",)), ("sales", ("tr_sales_no_delete",))):
                for trigger in triggers:
                    connection.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()
