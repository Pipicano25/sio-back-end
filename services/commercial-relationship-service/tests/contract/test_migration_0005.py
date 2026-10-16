"""Migración 0005 de la spec 021 (T008; CP-T08, CP-T11; DS-09, RC-021-1, RC-021-5, RC-021-10).

- Los datos existentes de `price_list_items` y `company_products` no cambian; las columnas nuevas quedan en NULL.
- Las exclusiones GiST impiden una presentación en dos políticas de la misma lista en el mismo instante.
- Los historiales solo admiten cerrar la vigencia; las solicitudes son inmutables; una aplicación en estado final
  no cambia.
- `downgrade` se detiene sin cambios si hay datos de la spec 021 y revierte limpio si no los hay.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.conftest import run_alembic

NEW_TABLES = {
    "price_list_pricing_policies",
    "price_list_pricing_policy_terms",
    "price_list_pricing_policy_presentations",
    "automatic_price_update_requests",
    "automatic_price_applications",
}


def _base_rows(connection) -> dict:
    """Empresa ficticia con un producto, una presentación, una lista y un precio manual."""
    ids = {name: uuid4() for name in ("company", "product", "presentation", "price_list", "item")}
    connection.execute(
        text(
            "INSERT INTO company_products (id, company_id, global_product_id, internal_code, display_name, currency_code, "
            "created_by, updated_by) VALUES (:product, :company, :g, 'ARZ-1', 'Arroz ficticio', 'COP', 'sub', 'sub')"
        ),
        {**ids, "g": uuid4()},
    )
    connection.execute(
        text(
            "INSERT INTO company_product_presentations (id, company_id, company_product_id, global_product_presentation_id, "
            "created_by, updated_by) VALUES (:presentation, :company, :product, :g, 'sub', 'sub')"
        ),
        {**ids, "g": uuid4()},
    )
    connection.execute(
        text(
            "INSERT INTO price_lists (id, company_id, code, name, currency_code, created_by, updated_by) "
            "VALUES (:price_list, :company, 'PUB', 'Público', 'COP', 'sub', 'sub')"
        ),
        ids,
    )
    connection.execute(
        text(
            "INSERT INTO price_list_items (id, company_id, price_list_id, company_product_id, company_product_presentation_id, "
            "unit_price, created_by, updated_by) VALUES (:item, :company, :price_list, :product, :presentation, 3500, 'sub', 'sub')"
        ),
        ids,
    )
    return ids


def _policy(connection, ids, name: str = "Alimentos") -> object:
    policy = uuid4()
    connection.execute(
        text(
            "INSERT INTO price_list_pricing_policies (id, company_id, price_list_id, name, created_by, updated_by) "
            "VALUES (:id, :company, :price_list, :name, 'sub', 'sub')"
        ),
        {"id": policy, "name": name, **ids},
    )
    return policy


def _assign(connection, ids, policy, valid_from: str = "2026-10-15T00:00:00Z", valid_to: str | None = None):
    closed = valid_to is not None
    connection.execute(
        text(
            "INSERT INTO price_list_pricing_policy_presentations (id, company_id, policy_id, price_list_id, "
            "company_product_presentation_id, valid_from, valid_to, created_by, closed_at, closed_by) VALUES "
            "(:id, :company, :policy, :price_list, :presentation, :valid_from, :valid_to, 'sub', "
            "CASE WHEN :closed THEN now() END, CASE WHEN :closed THEN 'sub' END)"
        ),
        {"id": uuid4(), "policy": policy, "valid_from": valid_from, "valid_to": valid_to, "closed": closed, **ids},
    )


def _cleanup(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE automatic_price_applications, automatic_price_update_requests, "
                "price_list_pricing_policy_presentations, price_list_pricing_policy_terms, price_list_pricing_policies, "
                "price_list_items, price_lists, company_product_presentations, company_products CASCADE"
            )
        )


@pytest.fixture
def engine(test_database_url, migrated_database):
    engine = create_engine(test_database_url)
    _cleanup(engine)
    yield engine
    _cleanup(engine)
    engine.dispose()


def test_upgrade_keeps_existing_rows_with_null_new_columns(test_database_url, engine) -> None:
    run_alembic(test_database_url, "downgrade", "0004")
    try:
        with engine.begin() as connection:
            ids = _base_rows(connection)
        run_alembic(test_database_url, "upgrade", "head")
        assert NEW_TABLES <= set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            item = connection.execute(
                text("SELECT unit_price, origin, closure_reason, automatic_application_id, version FROM price_list_items")
            ).one()
            assert (item.unit_price, item.origin, item.closure_reason, item.automatic_application_id, item.version) == (
                3500, None, None, None, 1
            )
            tax = connection.execute(
                text("SELECT purchase_tax_percentage FROM company_products WHERE id = :product"), ids
            ).scalar_one()
            assert tax is None  # sin configurar; no se asigna ningún valor (R-11)
    finally:
        run_alembic(test_database_url, "upgrade", "head")


def test_purchase_tax_percentage_range(engine) -> None:
    with engine.begin() as connection:
        ids = _base_rows(connection)
        for value in ("0", "19", "100", "12.3456"):
            connection.execute(text("UPDATE company_products SET purchase_tax_percentage = :v WHERE id = :product"), {"v": value, **ids})
    for value in ("-0.0001", "100.0001"):
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(text("UPDATE company_products SET purchase_tax_percentage = :v WHERE id = :product"), {"v": value, **ids})


def test_presentation_cannot_be_in_two_policies_of_the_same_list_at_once(engine) -> None:
    with engine.begin() as connection:
        ids = _base_rows(connection)
        food = _policy(connection, ids)
        cleaning = _policy(connection, ids, "Aseo")
        _assign(connection, ids, food)
    with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
        _assign(connection, ids, cleaning)
    assert "ex_price_list_pricing_policy_presentations_no_overlap" in str(raised.value)

    with engine.begin() as connection:  # rangos contiguos [a, b) y [b, …) no se solapan
        _assign(connection, ids, cleaning, valid_from="2026-01-01T00:00:00Z", valid_to="2026-10-15T00:00:00Z")


def test_history_only_allows_closing_once(engine) -> None:
    with engine.begin() as connection:
        ids = _base_rows(connection)
        policy = _policy(connection, ids)
        _assign(connection, ids, policy)
        connection.execute(
            text(
                "UPDATE price_list_pricing_policy_presentations SET valid_to = '2026-10-16T00:00:00Z', closed_at = now(), "
                "closed_by = 'sub'"
            )
        )
    with pytest.raises(DBAPIError), engine.begin() as connection:  # ya cerrado: no se reabre
        connection.execute(
            text("UPDATE price_list_pricing_policy_presentations SET valid_to = NULL, closed_at = NULL, closed_by = NULL")
        )
    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(text("DELETE FROM price_list_pricing_policy_presentations"))


def test_term_markup_range_and_single_term(engine) -> None:
    with engine.begin() as connection:
        ids = _base_rows(connection)
        policy = _policy(connection, ids)
        connection.execute(
            text(
                "INSERT INTO price_list_pricing_policy_terms (id, policy_id, markup_percentage, valid_from, created_by) "
                "VALUES (:id, :policy, 1000, '2026-10-15T00:00:00Z', 'sub')"
            ),
            {"id": uuid4(), "policy": policy},
        )
    for markup, valid_from in (("1000.0001", "2027-01-01T00:00:00Z"), ("20", "2026-11-01T00:00:00Z")):
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO price_list_pricing_policy_terms (id, policy_id, markup_percentage, valid_from, created_by) "
                    "VALUES (:id, :policy, :m, :f, 'sub')"
                ),
                {"id": uuid4(), "policy": policy, "m": markup, "f": valid_from},
            )


def _request_and_application(connection, ids) -> tuple:
    request = uuid4()
    connection.execute(
        text(
            "INSERT INTO automatic_price_update_requests (id, company_id, contract_version, purchase_id, purchase_detail_id, "
            "branch_id, company_product_id, company_product_presentation_id, sequence, currency_code, line_total, quantity, "
            "received_at, received_by_user_id, payload_hash, created_by) VALUES (:id, :company, 1, :p, :d, :b, :product, "
            ":presentation, 1, 'COP', 23800, 10, now(), :u, repeat('a', 64), 'service-account-purchase-service')"
        ),
        {"id": request, "p": uuid4(), "d": uuid4(), "b": uuid4(), "u": uuid4(), **ids},
    )
    application = uuid4()
    connection.execute(
        text(
            "INSERT INTO automatic_price_applications (id, company_id, request_id, price_list_id, "
            "company_product_presentation_id, sequence, created_by, updated_by) VALUES (:id, :company, :request, "
            ":price_list, :presentation, 1, 'sub', 'sub')"
        ),
        {"id": application, "request": request, **ids},
    )
    return request, application


def test_request_is_immutable_and_final_application_does_not_change(engine) -> None:
    with engine.begin() as connection:
        ids = _base_rows(connection)
        request, application = _request_and_application(connection, ids)
    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(text("UPDATE automatic_price_update_requests SET line_total = 1"))

    with engine.begin() as connection:  # PENDING → FAILED → APPLIED (final)
        connection.execute(text("UPDATE automatic_price_applications SET status = 'FAILED', attempts = 1"))
        connection.execute(text("UPDATE automatic_price_applications SET status = 'APPLIED', completed_at = now()"))
    with pytest.raises(DBAPIError), engine.begin() as connection:  # CP-T08
        connection.execute(text("UPDATE automatic_price_applications SET status = 'FAILED', completed_at = NULL"))
    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(text("DELETE FROM automatic_price_applications"))


def test_application_capture_is_immutable_and_checks_hold(engine) -> None:
    with engine.begin() as connection:
        ids = _base_rows(connection)
        _request_and_application(connection, ids)
    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(text("UPDATE automatic_price_applications SET sequence = 2"))
    with pytest.raises(IntegrityError), engine.begin() as connection:  # RESOLVED exige usuario y motivo
        connection.execute(text("UPDATE automatic_price_applications SET status = 'RESOLVED', completed_at = now()"))
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("UPDATE price_list_items SET closure_reason = 'OTRO'"))


def test_downgrade_guard_and_clean_downgrade(test_database_url, engine) -> None:
    with engine.begin() as connection:
        ids = _base_rows(connection)
        _policy(connection, ids)
    with pytest.raises(RuntimeError, match="eliminaría 1 políticas de precios"):
        run_alembic(test_database_url, "downgrade", "0004")
    assert NEW_TABLES <= set(inspect(engine).get_table_names())  # nada cambió

    _cleanup(engine)
    run_alembic(test_database_url, "downgrade", "0004")
    try:
        engine.dispose()
        tables = set(inspect(engine).get_table_names())
        assert not NEW_TABLES & tables
        columns = {column["name"] for column in inspect(engine).get_columns("price_list_items")}
        assert not {"origin", "closure_reason", "automatic_application_id"} & columns
    finally:
        run_alembic(test_database_url, "upgrade", "head")
