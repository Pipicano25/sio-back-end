"""Rendimiento (SC-001, SC-002, SC-005; research.md R-16; T077). Ejecutar con `pytest -m performance`.

- Confirmación de 100 líneas p95 ≤ 3 s con dobles de latencia realista (20 ms por llamada externa).
- 50 confirmaciones concurrentes del mismo período: números únicos y consecutivos.
- Consultas p95 ≤ 500 ms con 10 000 compras en la empresa.
"""

from __future__ import annotations

import statistics
import threading
import time
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.conftest import base, distinct_lines, line, new_key, purchase_body, user_sub

pytestmark = pytest.mark.performance

LATENCY = 0.02


def p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[max(0, int(len(ordered) * 0.95) - 1)]


def test_confirmation_of_100_lines(buyer, world, fakes, make_sequence) -> None:
    make_sequence()
    for availability in fakes.all_availability():
        availability.latency = LATENCY
    samples = []
    for _ in range(10):
        lines = [  # spec 021: cada línea con su propia presentación
            *distinct_lines(fakes, world.product, 50, "3", "1500"),
            *distinct_lines(fakes, world.product_2, 50, "3", "1500"),
        ]
        draft = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, *lines))
        assert draft.status_code == 201, draft.text
        started = time.perf_counter()
        response = buyer.post(
            f"{base(world)}/purchases/{draft.json()['id']}/confirmation",
            json={"version": draft.json()["version"]},
            headers={"Idempotency-Key": new_key()},
        )
        assert response.status_code == 200, response.text
        received = buyer.post(  # spec 020: la recepción es la que aplica la entrada en Inventory
            f"{base(world)}/purchases/{draft.json()['id']}/receipt",
            json={"version": response.json()["version"], "full_receipt_confirmed": True},
            headers={"Idempotency-Key": new_key()},
        )
        samples.append(time.perf_counter() - started)
        assert received.status_code == 200, received.text
    print(f"\nconfirmación y recepción de 100 líneas: p95={p95(samples):.3f}s mediana={statistics.median(samples):.3f}s")
    assert p95(samples) <= 3.0


def test_fifty_concurrent_confirmations(test_client, user_token, world, fakes, make_sequence, make_draft) -> None:
    make_sequence()
    drafts = [make_draft() for _ in range(50)]
    barrier = threading.Barrier(50)
    confirmed: list[dict] = []
    received: list[dict] = []
    errors: list[str] = []
    lock = threading.Lock()
    token = user_token("compras.test")

    def run(purchase, action: str, body: dict, results: list) -> None:
        barrier.wait(30)
        response = test_client.post(
            f"{base(world)}/purchases/{purchase['id']}/{action}",
            json=body,
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": new_key()},
        )
        with lock:
            if response.status_code == 200:
                results.append(response.json())
            else:
                errors.append(response.text)

    def concurrently(purchases, action: str, body, results: list) -> None:
        threads = [threading.Thread(target=run, args=(item, action, body(item), results)) for item in purchases]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(120)

    concurrently(drafts, "confirmation", lambda draft: {"version": draft["version"]}, confirmed)
    assert not errors, errors[:3]
    assert sorted(item["number"] for item in confirmed) == [f"CP-{value:06d}" for value in range(1, 51)]
    assert fakes.inventory.entries() == []  # spec 020: confirmar no mueve inventario

    barrier = threading.Barrier(50)
    concurrently(confirmed, "receipt", lambda item: {"version": item["version"], "full_receipt_confirmed": True}, received)
    assert not errors, errors[:3]
    assert len(received) == 50 and len(fakes.inventory.entries()) == 50


def seed_purchases(engine, world, count: int, application_user) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO purchases (id, company_id, branch_id, company_supplier_id, payment_condition_code_snapshot,
                    payment_terms_days_snapshot, due_date, status, operation_date, supplier_name_snapshot,
                    supplier_identification_snapshot, currency_code, subtotal, discount_total, tax_total, total,
                    created_by_user_id, created_by, updated_by)
                SELECT gen_random_uuid(), :company, :branch, :supplier, 'CASH', 0, d, 'DRAFT', d, 'Proveedor ficticio',
                       'NIT 900', 'COP', 100, 0, 0, 100, :user, 'sub-perf', 'sub-perf'
                  FROM (SELECT (date '2025-01-01' + (g % 600)) AS d FROM generate_series(1, :n) AS g) AS days
                """
            ),
            {"company": world.company, "branch": world.branch, "supplier": world.supplier, "user": application_user, "n": count},
        )
        connection.execute(text("ANALYZE purchases"))


def test_queries_with_ten_thousand_purchases(buyer, world, fakes, test_engine) -> None:
    seed_purchases(test_engine, world, 10_000, fakes.oc.members[(user_sub("compras.test"), world.company)])
    draft = buyer.post(f"{base(world)}/purchases", json=purchase_body(world, line(world.product))).json()
    calls = [
        lambda: buyer.get(f"{base(world)}/purchases"),
        lambda: buyer.get(f"{base(world)}/purchases", params={"status": "DRAFT", "page": 50, "page_size": 100}),
        lambda: buyer.get(f"{base(world)}/purchases", params={"operation_date_from": "2025-06-01", "operation_date_to": "2025-06-30"}),
        lambda: buyer.get(f"{base(world)}/purchases/{draft['id']}"),
    ]
    for call in calls:
        samples = []
        for _ in range(20):
            started = time.perf_counter()
            response = call()
            samples.append(time.perf_counter() - started)
            assert response.status_code == 200
        print(f"\nconsulta: p95={p95(samples) * 1000:.0f}ms")
        assert p95(samples) <= 0.5
    assert buyer.get(f"{base(world)}/purchases").json()["total_records"] == 10_001


def test_today(world) -> None:
    assert date.today() and uuid4()
