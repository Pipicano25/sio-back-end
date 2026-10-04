"""SC-009: primera página de búsqueda con 50 000 productos por empresa < 1 s p95 (R-13).

Marcador `performance`: no corre con la suite ordinaria (`pytest -m performance`).
"""

from __future__ import annotations

import statistics
import time
from uuid import uuid4

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.performance

TOTAL = 50_000
SAMPLES = 40


def _load(engine, company):
    rows = [
        {
            "id": uuid4(),
            "company_id": company,
            "global_product_id": uuid4(),
            "internal_code": f"{index:06d}",
            "reference_code": f"REF-{index % 997}",
            "display_name": f"Producto sintético {index:06d} {'ACETAMINOFEN' if index % 500 == 0 else 'GENERICO'}",
        }
        for index in range(TOTAL)
    ]
    with engine.begin() as connection:
        for start in range(0, TOTAL, 5_000):
            connection.execute(
                text(
                    "INSERT INTO company_products (id, company_id, global_product_id, internal_code, "
                    "reference_code, display_name, currency_code, created_by, updated_by) VALUES "
                    "(:id, :company_id, :global_product_id, :internal_code, :reference_code, :display_name, "
                    "'COP', 'perf', 'perf')"
                ),
                rows[start : start + 5_000],
            )
        connection.execute(text("ANALYZE company_products"))


@pytest.mark.parametrize("search", ["acetaminofen", "0123", "ref-5", None])
def test_first_page_p95_under_one_second(test_engine, as_user, company, search):
    _load(test_engine, company)
    client = as_user("consulta.test")
    params = {"page": 1, "page_size": 20}
    if search:
        params["search"] = search

    durations = []
    for _ in range(SAMPLES):
        started = time.perf_counter()
        response = client.get(f"/api/v1/companies/{company}/company-products", params=params)
        durations.append(time.perf_counter() - started)
        assert response.status_code == 200

    p95 = statistics.quantiles(durations, n=20)[18]
    assert p95 < 1.0, f"p95={p95:.3f}s con search={search!r}"
