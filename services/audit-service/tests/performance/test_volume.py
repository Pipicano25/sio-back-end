"""Volumen y tiempos de respuesta (SC-006; T034, T041). Ejecutar con `pytest -m performance`.

Carga 1 000 000 de eventos (10 empresas y plataforma) con `INSERT … SELECT generate_series`
y mide la primera página de listados e historial (p95 < 1 s) y el registro de lotes de 100
(p95 < 1 s).
"""

from __future__ import annotations

import statistics
import time
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.conftest import PLATFORM_READ, READ, event_body, user_sub

pytestmark = pytest.mark.performance

TOTAL = 1_000_000
COMPANIES = 10
SAMPLES = 20


def _p95(durations: list[float]) -> float:
    return statistics.quantiles(durations, n=20)[18]


@pytest.fixture
def loaded(test_engine, clean_database) -> dict:
    companies = [str(uuid4()) for _ in range(COMPANIES)]
    entity = str(uuid4())

    with test_engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO audit_events (event_id, company_id, action, entity_type, entity_id,
                    new_values, result, source_service, occurred_at, content_hash, created_by, updated_by)
                SELECT gen_random_uuid(),
                       CASE WHEN g % 11 = 0 THEN NULL ELSE (CAST(:companies AS text[]))[1 + g % 10]::uuid END,
                       (ARRAY['CREATE','UPDATE','INACTIVATE','CHANGE_PRICE'])[1 + g % 4],
                       (ARRAY['PriceListItem','PriceList','CompanySupplier'])[1 + g % 3],
                       CASE WHEN g % 1000 = 0 THEN CAST(:entity AS uuid) ELSE gen_random_uuid() END,
                       jsonb_build_object('n', g),
                       CASE WHEN g % 7 = 0 THEN 'FAILURE' ELSE 'SUCCESS' END,
                       'perf-emitter',
                       now() - (g || ' seconds')::interval,
                       md5(g::text) || md5((g + 1)::text),
                       'sub-perf', 'sub-perf'
                FROM generate_series(1, :total) AS g
                """
            ),
            {"companies": companies, "entity": entity, "total": TOTAL},
        )
        connection.execute(text("ANALYZE audit_events"))

    return {"companies": companies, "entity": entity}


def test_query_first_page_p95_under_one_second(loaded, as_token, make_token, fake_oc) -> None:
    client = as_token(make_token(READ, PLATFORM_READ, sub=user_sub("perf"), preferred_username="perf"))
    company = loaded["companies"][0]
    fake_oc.add_member(user_sub("perf"), __import__("uuid").UUID(company))

    urls = [
        (f"/api/v1/companies/{company}/audit-events", {"action": "UPDATE", "result": "SUCCESS"}),
        (f"/api/v1/companies/{company}/audit-events", {}),
        (f"/api/v1/companies/{company}/entity-history/PriceListItem/{loaded['entity']}", {}),
        ("/api/v1/platform-audit-events", {"entity_type": "PriceList"}),
        (f"/api/v1/platform-entity-history/PriceListItem/{loaded['entity']}", {}),
    ]

    for url, params in urls:
        durations = []
        for _ in range(SAMPLES):
            started = time.perf_counter()
            response = client.get(url, params=params)
            durations.append(time.perf_counter() - started)
            assert response.status_code == 200
        assert _p95(durations) < 1.0, (url, _p95(durations))


def test_batch_of_hundred_p95_under_one_second(emitter, clean_database) -> None:
    durations = []
    for _ in range(SAMPLES):
        events = [event_body() for _ in range(100)]
        started = time.perf_counter()
        response = emitter.post("/api/v1/audit-events/batch", json={"events": events})
        durations.append(time.perf_counter() - started)
        assert response.status_code == 200
    assert _p95(durations) < 1.0, _p95(durations)
