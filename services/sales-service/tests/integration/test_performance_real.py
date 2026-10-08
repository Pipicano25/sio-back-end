"""Confirmación de 100 líneas con servicios reales (SC-001; T083). `pytest -m "integration and performance"`."""

from __future__ import annotations

import threading
import time

import pytest

from tests.integration.support import SALES, _adopt, balance, draft_body, new_key, stock_with_purchase

pytestmark = [pytest.mark.integration, pytest.mark.performance]


def test_confirmation_of_100_lines_with_real_services(admin, seller, real_world, sequence) -> None:
    samples_wanted = int(__import__("os").environ.get("SALES_PERF_SAMPLES", "5"))
    units = str(100 * samples_wanted + 100)
    stock_with_purchase(admin, real_world, [(real_world.product, units, "1000"), (real_world.product_2, units, "6000")])
    lines = [
        {
            "company_product_id": (real_world.product if index % 2 else real_world.product_2).company_product,
            "quantity": "2",
        }
        for index in range(100)
    ]
    samples = []
    for _ in range(samples_wanted):
        draft = seller.post(f"{SALES}/companies/{real_world.company}/sales", json=draft_body(real_world, *lines))
        assert draft.status_code == 201, draft.text
        started = time.perf_counter()
        response = seller.post(
            f"{SALES}/companies/{real_world.company}/sales/{draft.json()['id']}/confirmation",
            json={"version": draft.json()["version"]},
            headers={"Idempotency-Key": new_key()},
        )
        samples.append(time.perf_counter() - started)
        assert response.status_code == 200, response.text
    ordered = sorted(samples)
    p95 = ordered[max(0, round(0.95 * len(ordered)) - 1)]
    worst = max(samples)
    print(f"\nconfirmación de 100 líneas con servicios reales: p95={p95:.3f}s máx={worst:.3f}s muestras={[round(s, 3) for s in samples]}")
    assert p95 <= 3.0  # SC-001: p95 ≤ 3 s


def test_twenty_concurrent_sales_of_the_last_unit_with_real_inventory(admin, seller, real_world, sequence) -> None:
    """SC-003 / RC-04: exactamente una venta se lleva la última unidad; Inventory real es la barrera."""
    import secrets

    product = _adopt(admin, real_world.company, f"U{secrets.token_hex(2).upper()}", sale_price="1500.00",
                     inventory_control=True, with_box=False)
    stock_with_purchase(admin, real_world, [(product, "1", "1000")])
    drafts = []
    for _ in range(20):
        response = seller.post(f"{SALES}/companies/{real_world.company}/sales",
                               json=draft_body(real_world, {"company_product_id": product.company_product, "quantity": "1"}))
        assert response.status_code == 201, response.text
        drafts.append(response.json())
    barrier = threading.Barrier(len(drafts))
    statuses: list[int] = []
    lock = threading.Lock()

    def attempt(draft) -> None:
        barrier.wait(30)
        response = seller.post(
            f"{SALES}/companies/{real_world.company}/sales/{draft['id']}/confirmation",
            json={"version": draft["version"]},
            headers={"Idempotency-Key": new_key()},
        )
        with lock:
            statuses.append(response.status_code)

    threads = [threading.Thread(target=attempt, args=(draft,)) for draft in drafts]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)
    print(f"\n20 ventas concurrentes de la última unidad: {sorted(statuses)}")
    assert sorted(statuses) == [200] + [409] * 19
    assert balance(admin, real_world, product) == 0
