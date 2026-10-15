"""Migración `0002` (spec 020): columnas, restricciones, trigger reemplazado y guardas (DS-09)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text

from tests.conftest import run_alembic

NEW_COLUMNS = {
    "payment_method_id",
    "payment_method_code_snapshot",
    "payment_method_name_snapshot",
    "received_at",
    "received_by_user_id",
}
NEW_CHECKS = {
    "ck_purchases_receipt",
    "ck_purchases_cash_only",
    "ck_purchases_payment_method_snapshot",
    "ck_purchases_payment_method_required",
    "ck_purchase_details_presentation_required",
    "ck_purchase_details_net_cost",
}


def _checks(engine) -> dict[str, str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE contype = 'c'")
        ).all()
    return dict(rows)


def _insert_credit_draft(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO purchases (id, company_id, branch_id, company_supplier_id, payment_condition_code_snapshot, "
                "payment_terms_days_snapshot, due_date, status, operation_date, supplier_name_snapshot, "
                "supplier_identification_snapshot, currency_code, created_by_user_id, created_by, updated_by) "
                "VALUES (:id, :c, :b, :s, 'CREDIT', 30, DATE '2026-11-13', 'DRAFT', DATE '2026-10-14', 'Proveedor', "
                "'NIT 900', 'COP', :u, 'sub', 'sub')"
            ),
            {"id": uuid4(), "c": uuid4(), "b": uuid4(), "s": uuid4(), "u": uuid4()},
        )


def test_upgrade_adds_columns_and_rules_and_downgrade_restores_0001(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        columns = {column["name"] for column in inspect(engine).get_columns("purchases")}
        assert NEW_COLUMNS <= columns
        checks = _checks(engine)
        assert NEW_CHECKS <= set(checks)
        assert "RECEIVE" in checks["ck_purchase_operations_operation_type"]
        assert "unit_cost > " in checks["ck_purchase_details_unit_cost"] and ">=" not in checks["ck_purchase_details_unit_cost"]

        run_alembic(test_database_url, "downgrade", "0001")
        inspector = inspect(engine)
        assert not NEW_COLUMNS & {column["name"] for column in inspector.get_columns("purchases")}
        checks = _checks(engine)
        assert not NEW_CHECKS & set(checks)
        assert "RECEIVE" not in checks["ck_purchase_operations_operation_type"]
        assert "(inventory_operation_id IS NOT NULL) AND (cancelled_by_user_id IS NULL)" in checks["ck_purchases_lifecycle"]
    finally:
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()


def test_guard_stops_without_changes_when_a_credit_purchase_exists(test_database_url, clean_database) -> None:
    """DS-09: una compra a crédito existente detiene la migración; la base queda en la `0001`."""
    engine = create_engine(test_database_url)
    try:
        run_alembic(test_database_url, "downgrade", "0001")
        _insert_credit_draft(engine)

        with pytest.raises(RuntimeError, match="no son de contado"):
            run_alembic(test_database_url, "upgrade", "head")

        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001"
        assert not NEW_COLUMNS & {column["name"] for column in inspect(engine).get_columns("purchases")}
    finally:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE purchases DISABLE TRIGGER tr_purchases_no_delete"))
            connection.execute(text("DELETE FROM purchases"))
            connection.execute(text("ALTER TABLE purchases ENABLE TRIGGER tr_purchases_no_delete"))
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()
