"""Pruebas de volumen (SC-002, SC-003). Marcadas `performance`: no corren por defecto.

Ejecutar con: `pytest -m performance tests/contract/test_performance.py`
"""

import statistics
import time

import pytest
from sqlalchemy import text

from tests import factories

pytestmark = pytest.mark.performance

PRODUCTS = 500_000


@pytest.fixture
def large_catalog(test_engine, session_factory):
    unit = factories.unit(session_factory)
    with test_engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO global_products
                    (id, product_type, canonical_name, canonical_name_key, base_unit_id, status,
                     version, created_at, updated_at, created_by, updated_by)
                SELECT gen_random_uuid(), 'GOOD', 'Producto ' || n, 'producto ' || n, :unit, 'ACTIVE',
                       1, now(), now(), 'perf', 'perf'
                FROM generate_series(1, :total) AS n
                """
            ),
            {"unit": unit.id, "total": PRODUCTS},
        )
        connection.execute(
            text(
                """
                INSERT INTO global_product_identifiers
                    (id, global_product_id, identifier_type, value, canonical_value, is_primary, status,
                     version, created_at, updated_at, created_by, updated_by)
                SELECT gen_random_uuid(), id, 'BARCODE', 'PERF' || replace(canonical_name_key, ' ', ''),
                       'PERF' || replace(canonical_name_key, ' ', ''), false, 'ACTIVE', 1, now(), now(),
                       'perf', 'perf'
                FROM global_products
                """
            )
        )
        connection.execute(text("ANALYZE global_products; ANALYZE global_product_identifiers"))
        ids = [row[0] for row in connection.execute(text("SELECT id FROM global_products LIMIT 100"))]
    return ids


def _p95(samples: list[float]) -> float:
    return statistics.quantiles(samples, n=20)[18]


def test_identifier_lookup_under_one_second(api, large_catalog) -> None:
    samples = []
    for n in range(1, 41):
        started = time.perf_counter()
        response = api.get(f"/api/v1/products/by-identifier/PERFproducto{n * 1000}")
        samples.append(time.perf_counter() - started)
        assert response.status_code == 200
    assert _p95(samples) < 1.0


def test_batch_lookup_of_100_under_two_seconds(api, large_catalog) -> None:
    ids = [str(item) for item in large_catalog]
    samples = []
    for _ in range(20):
        started = time.perf_counter()
        response = api.post("/api/v1/products/batch-lookup", json={"ids": ids})
        samples.append(time.perf_counter() - started)
        assert response.status_code == 200
    assert _p95(samples) < 2.0
