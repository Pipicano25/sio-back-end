"""Migración `0003` (spec 021, B-4): ventas sin impuesto adicional y su guarda (T060; CP-T11; DS-09)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import run_alembic
from tests.contract.db_rows import insert_detail


def checks(engine) -> set[str]:
    with engine.connect() as connection:
        return set(connection.execute(text("SELECT conname FROM pg_constraint WHERE contype = 'c'")).scalars())


def _sale(connection) -> object:
    sale = uuid4()
    connection.execute(
        text(
            "INSERT INTO sales (id, company_id, branch_id, company_customer_id, payment_condition_code_snapshot, "
            "payment_terms_days_snapshot, due_date, status, operation_date, customer_name_snapshot, "
            "customer_identification_snapshot, currency_code, created_by_user_id, created_by, updated_by) "
            "VALUES (:id, :c, :b, :cu, 'CASH', 0, DATE '2026-10-15', 'DRAFT', DATE '2026-10-15', 'Cliente ficticio', "
            "'CC 1', 'COP', :u, 'sub', 'sub')"
        ),
        {"id": sale, "c": uuid4(), "b": uuid4(), "cu": uuid4(), "u": uuid4()},
    )
    return sale


def _purge(engine) -> None:
    with engine.begin() as connection:
        for table, trigger in (("sale_details", "tr_sale_details_draft_only"), ("sales", "tr_sales_no_delete")):
            connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))
        connection.execute(text("DELETE FROM sale_details"))
        connection.execute(text("DELETE FROM sales"))
        for table, trigger in (("sale_details", "tr_sale_details_draft_only"), ("sales", "tr_sales_no_delete")):
            connection.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))


def test_upgrade_adds_the_check_and_downgrade_removes_it(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        assert "ck_sale_details_no_tax" in checks(engine)
        with pytest.raises(IntegrityError), engine.begin() as connection:
            insert_detail(connection, _sale(connection), tax_amount=1, total=11)
        run_alembic(test_database_url, "downgrade", "0002")
        assert "ck_sale_details_no_tax" not in checks(engine)
    finally:
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()


def test_guard_stops_without_changes_when_a_tax_exists(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        run_alembic(test_database_url, "downgrade", "0002")
        with engine.begin() as connection:
            insert_detail(connection, _sale(connection), tax_amount=1, total=11)
        with pytest.raises(RuntimeError, match="líneas de venta con impuesto"):
            run_alembic(test_database_url, "upgrade", "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002"
        assert "ck_sale_details_no_tax" not in checks(engine)
    finally:
        _purge(engine)
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()
