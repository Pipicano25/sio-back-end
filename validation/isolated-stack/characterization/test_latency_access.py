"""Latencia de la verificación de acceso con `http` y con `contract` (spec 025, T018 para el MVP).

Solo se ejecuta con `SIO_CHARACTERIZATION_LATENCY=<archivo.json>`: mide `SAMPLES` solicitudes por consumidor
(después de `WARMUP` de calentamiento) contra una empresa donde `admin.sio` es miembro activo, y agrega al archivo
el p50 y el p99 del lado del cliente junto con el origen de lecturas de la pila. No compara contra ningún umbral.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path

import pytest
from conftest import URLS, expect

TARGET = os.environ.get("SIO_CHARACTERIZATION_LATENCY", "").strip()
pytestmark = pytest.mark.skipif(not TARGET, reason="Medición opcional: definir SIO_CHARACTERIZATION_LATENCY.")
WARMUP, SAMPLES = 20, 200
PATHS = {
    "sales": lambda company: f"{URLS['sales']}/companies/{company}/sales",
    "inventory": lambda company: f"{URLS['inventory']}/companies/{company}/inventory-adjustments",
}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))]


@pytest.fixture(scope="module")
def company(seed, users, run_id):
    admin = users("admin.sio")
    colombia = expect(admin.get(f"{URLS['geography']}/global-countries", params={"iso3_code": "COL"}))["items"][0]["id"]
    company_id = seed.company(admin, colombia, f"LAT{run_id}")
    seed.member(admin, colombia, company_id, "admin.sio")
    return company_id


@pytest.mark.parametrize("consumer", sorted(PATHS))
def test_access_latency(company, users, reads, consumer):
    client = users("admin.sio")
    url = PATHS[consumer](company)
    for _ in range(WARMUP):
        assert client.get(url, params={"page_size": 1}).status_code == 200
    samples = []
    for _ in range(SAMPLES):
        started = time.perf_counter()
        response = client.get(url, params={"page_size": 1})
        samples.append((time.perf_counter() - started) * 1000)
        assert response.status_code == 200
    result = {"consumer": consumer, "reads": reads, "samples": SAMPLES, "p50_ms": round(statistics.median(samples), 2),
              "p99_ms": round(percentile(samples, 0.99), 2)}
    path = Path(TARGET)
    existing = json.loads(path.read_text()) if path.exists() else []
    path.write_text(json.dumps([*existing, result], indent=2))
