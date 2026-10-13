"""SC-007 de la 010: precio aplicable de 100 líneas < 1 s con 50 000 productos y 10 listas (T063; R-10).

Marcador `performance`: no corre con la suite ordinaria (`pytest -m performance`).
Además verifica que la resolución use a lo sumo 3 consultas SQL por solicitud.
"""

from __future__ import annotations

import statistics
import time
from uuid import uuid4

import pytest
from sqlalchemy import event, text

pytestmark = pytest.mark.performance

PRODUCTS = 50_000
LISTS = 10
SAMPLES = 30


def _load(engine, company):
    # Spec 019: cada producto con su presentación unidad; el precio es de la presentación.
    products = [{"id": uuid4(), "company_id": company, "global_product_id": uuid4(), "code": f"{index:06d}",
                 "presentation": uuid4(), "global_presentation": uuid4()}
                for index in range(PRODUCTS)]
    lists = [{"id": uuid4(), "company_id": company, "code": f"L{index}", "is_default": index == 0} for index in range(LISTS)]

    with engine.begin() as connection:
        for start in range(0, PRODUCTS, 5_000):
            connection.execute(
                text(
                    "INSERT INTO company_products (id, company_id, global_product_id, internal_code, display_name, "
                    "currency_code, created_by, updated_by) VALUES "
                    "(:id, :company_id, :global_product_id, :code, :code, 'COP', 'perf', 'perf')"
                ),
                products[start : start + 5_000],
            )
            connection.execute(
                text(
                    "INSERT INTO company_product_presentations (id, company_id, company_product_id, "
                    "global_product_presentation_id, status, created_by, updated_by) VALUES "
                    "(:presentation, :company_id, :id, :global_presentation, 'ACTIVE', 'perf', 'perf')"
                ),
                products[start : start + 5_000],
            )
        connection.execute(
            text(
                "INSERT INTO price_lists (id, company_id, code, name, currency_code, is_default, created_by, updated_by) "
                "VALUES (:id, :company_id, :code, :code, 'COP', :is_default, 'perf', 'perf')"
            ),
            lists,
        )
        # Un precio por presentación en cada lista para los primeros 5 000 productos (50 000 precios).
        prices = [
            {"id": uuid4(), "company_id": company, "list": price_list["id"], "product": product["id"],
             "presentation": product["presentation"]}
            for price_list in lists
            for product in products[:5_000]
        ]
        for start in range(0, len(prices), 5_000):
            connection.execute(
                text(
                    "INSERT INTO price_list_items (id, company_id, price_list_id, company_product_id, "
                    "company_product_presentation_id, unit_price, valid_from, created_by, updated_by) VALUES "
                    "(:id, :company_id, :list, :product, :presentation, 1500, '2026-01-01T00:00:00Z', 'perf', 'perf')"
                ),
                prices[start : start + 5_000],
            )
        connection.execute(text("ANALYZE company_products"))
        connection.execute(text("ANALYZE price_list_items"))

    return products


def test_100_lines_under_one_second_with_at_most_three_queries(test_engine, app, as_user, company):
    products = _load(test_engine, company)
    lines = [{"company_product_id": str(product["id"]), "company_product_presentation_id": str(product["presentation"])}
             for product in products[4_950:5_050]]
    client = as_user("ventas.test")
    url = f"/api/v1/companies/{company}/applicable-prices/resolve"
    body = {"lines": lines, "at": "2026-10-05T12:00:00Z"}

    statements: list[str] = []
    engine = app.state.database.engine

    def count(conn, cursor, statement, parameters, context, executemany):
        if "price_list" in statement or "company_product" in statement:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        response = client.post(url, json=body)
    finally:
        event.remove(engine, "before_cursor_execute", count)

    assert response.status_code == 200, response.text
    assert len(statements) <= 3, statements
    resolutions = {item["resolution"] for item in response.json()["items"]}
    assert resolutions == {"PRICE_LIST_ITEM", "NO_PRICE_IN_LIST"}  # spec 019: sin respaldo

    durations = []
    for _ in range(SAMPLES):
        started = time.perf_counter()
        assert client.post(url, json=body).status_code == 200
        durations.append(time.perf_counter() - started)

    p95 = statistics.quantiles(durations, n=20)[18]
    assert p95 < 1.0, f"p95={p95:.3f}s"
