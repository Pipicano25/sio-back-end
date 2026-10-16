"""Migración `0003` (spec 021): tasa por línea, sin presentaciones repetidas, serie de costos y outbox (T014).

CP-56 (la guarda detiene la migración sin cambios), CP-T11 (`upgrade`/`downgrade` sin tocar filas existentes) y
las reglas de inmutabilidad de la serie y del outbox (R-03, EXC-001).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

from tests.conftest import TABLES, TRIGGERS, run_alembic

NEW_TABLES = {"purchase_presentation_cost_series", "purchase_price_update_outbox"}
NEW_COLUMNS = {"tax_percentage", "tax_percentage_source"}


def _draft(connection, lines: list[tuple[object, object]]) -> object:
    """Borrador de contado ficticio con una línea por `(producto, presentación)`."""
    purchase = uuid4()
    connection.execute(
        text(
            "INSERT INTO purchases (id, company_id, branch_id, company_supplier_id, payment_condition_code_snapshot, "
            "payment_terms_days_snapshot, due_date, status, operation_date, supplier_name_snapshot, "
            "supplier_identification_snapshot, currency_code, created_by_user_id, created_by, updated_by) "
            "VALUES (:id, :c, :b, :s, 'CASH', 0, DATE '2026-10-15', 'DRAFT', DATE '2026-10-15', 'Proveedor ficticio', "
            "'NIT 900000000', 'COP', :u, 'sub', 'sub')"
        ),
        {"id": purchase, "c": uuid4(), "b": uuid4(), "s": uuid4(), "u": uuid4()},
    )
    for number, (product, presentation) in enumerate(lines, start=1):
        connection.execute(
            text(
                "INSERT INTO purchase_details (id, purchase_id, line_number, company_product_id, "
                "company_product_presentation_id, product_code_snapshot, product_name_snapshot, "
                "presentation_code_snapshot, presentation_name_snapshot, unit_code_snapshot, quantity, unit_cost, "
                "tax_amount, subtotal, total, created_by, updated_by) VALUES (:id, :p, :n, :product, :presentation, "
                "'ARZ', 'Arroz ficticio', 'B1', 'Bolsa', 'UND', 10, 2000, 3800, 20000, 23800, 'sub', 'sub')"
            ),
            {"id": uuid4(), "p": purchase, "n": number, "product": product, "presentation": presentation},
        )
    return purchase


def _purge(engine) -> None:
    """Vacía la base de pruebas en la revisión actual (con o sin las tablas de la 0003)."""
    existing = set(inspect(engine).get_table_names())
    with engine.begin() as connection:
        for table, triggers in TRIGGERS.items():
            for trigger in triggers:
                connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))
        connection.execute(text(f"TRUNCATE TABLE {', '.join(t for t in TABLES if t in existing)}"))
        for table, triggers in TRIGGERS.items():
            for trigger in triggers:
                connection.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))


def test_upgrade_keeps_existing_lines_with_null_tax_percentage(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        run_alembic(test_database_url, "downgrade", "0002")
        with engine.begin() as connection:
            _draft(connection, [(uuid4(), uuid4())])
        run_alembic(test_database_url, "upgrade", "head")
        inspector = inspect(engine)
        assert NEW_TABLES <= set(inspector.get_table_names())
        assert NEW_COLUMNS <= {column["name"] for column in inspector.get_columns("purchase_details")}
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT tax_amount, total, tax_percentage, tax_percentage_source FROM purchase_details")
            ).one()
        assert (row.tax_amount, row.total, row.tax_percentage, row.tax_percentage_source) == (3800, 23800, None, None)
    finally:
        _purge(engine)
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()


def test_cp56_guard_stops_without_changes_with_repeated_presentations(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        run_alembic(test_database_url, "downgrade", "0002")
        product, presentation = uuid4(), uuid4()
        with engine.begin() as connection:
            _draft(connection, [(product, presentation), (product, presentation)])
        with pytest.raises(RuntimeError, match="misma presentación en más de una línea"):
            run_alembic(test_database_url, "upgrade", "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002"
        assert not NEW_TABLES & set(inspect(engine).get_table_names())
    finally:
        _purge(engine)
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()


def test_unique_presentation_and_tax_percentage_checks(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        product, presentation = uuid4(), uuid4()
        with pytest.raises(DBAPIError, match="uq_purchase_details_purchase_presentation"), engine.begin() as connection:
            _draft(connection, [(product, presentation), (product, presentation)])
        with engine.begin() as connection:
            _draft(connection, [(product, presentation), (product, uuid4())])  # CP-30: otra presentación del producto
            connection.execute(text("UPDATE purchase_details SET tax_percentage = 19, tax_percentage_source = 'PRODUCT_DEFAULT'"))
        for statement in (
            "UPDATE purchase_details SET tax_percentage = 100.0001, tax_percentage_source = 'LINE_OVERRIDE'",
            "UPDATE purchase_details SET tax_percentage = NULL",  # origen sin tasa
            "UPDATE purchase_details SET tax_percentage_source = 'OTRO'",
        ):
            with pytest.raises(DBAPIError), engine.begin() as connection:
                connection.execute(text(statement))
    finally:
        engine.dispose()


def _series_and_outbox(connection) -> dict:
    purchase = _draft(connection, [(uuid4(), uuid4())])
    detail, presentation = connection.execute(
        text("SELECT id, company_product_presentation_id FROM purchase_details WHERE purchase_id = :p"), {"p": purchase}
    ).one()
    ids = {"c": uuid4(), "presentation": presentation, "detail": detail, "purchase": purchase}
    connection.execute(
        text(
            "INSERT INTO purchase_presentation_cost_series (company_id, company_product_presentation_id, last_sequence, "
            "last_purchase_detail_id, last_line_total, last_quantity) VALUES (:c, :presentation, 1, :detail, 23800, 10)"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO purchase_price_update_outbox (id, company_id, company_product_presentation_id, sequence, "
            "purchase_id, purchase_detail_id, payload, created_by) VALUES (:id, :c, :presentation, 1, :purchase, "
            ":detail, '{\"contract_version\": 1}', 'sub')"
        ),
        {"id": uuid4(), **ids},
    )
    return ids


def test_cost_series_only_advances_one_by_one(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        with engine.begin() as connection:
            _series_and_outbox(connection)
            connection.execute(text("UPDATE purchase_presentation_cost_series SET last_sequence = 2"))
        for statement in (
            "UPDATE purchase_presentation_cost_series SET last_sequence = 4",
            "UPDATE purchase_presentation_cost_series SET last_sequence = 1",
            "DELETE FROM purchase_presentation_cost_series",
        ):
            with pytest.raises(DBAPIError), engine.begin() as connection:
                connection.execute(text(statement))
    finally:
        engine.dispose()


def test_outbox_content_is_immutable_and_delivery_is_final(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        with engine.begin() as connection:
            _series_and_outbox(connection)
            connection.execute(text("UPDATE purchase_price_update_outbox SET attempts = 1, last_error_code = 'TIMEOUT'"))
        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(text("UPDATE purchase_price_update_outbox SET payload = '{}'"))
        with engine.begin() as connection:
            connection.execute(text("UPDATE purchase_price_update_outbox SET status = 'DELIVERED', delivered_at = now()"))
        for statement in (
            "UPDATE purchase_price_update_outbox SET attempts = 2",
            "DELETE FROM purchase_price_update_outbox",
        ):
            with pytest.raises(DBAPIError), engine.begin() as connection:
                connection.execute(text(statement))
    finally:
        engine.dispose()


def test_downgrade_guard_and_clean_downgrade(test_database_url, clean_database) -> None:
    engine = create_engine(test_database_url)
    try:
        with engine.begin() as connection:
            _series_and_outbox(connection)
        with pytest.raises(RuntimeError, match="solicitudes de actualización de precio"):
            run_alembic(test_database_url, "downgrade", "0002")
        assert NEW_TABLES <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    _purge(engine)
    run_alembic(test_database_url, "downgrade", "0002")
    try:
        engine = create_engine(test_database_url)
        assert not NEW_TABLES & set(inspect(engine).get_table_names())
        assert not NEW_COLUMNS & {column["name"] for column in inspect(engine).get_columns("purchase_details")}
    finally:
        run_alembic(test_database_url, "upgrade", "head")
        engine.dispose()
