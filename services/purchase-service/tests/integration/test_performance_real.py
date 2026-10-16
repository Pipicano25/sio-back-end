"""Confirmación y recepción de 100 líneas con servicios reales (SC-001; T077; spec 020). `pytest -m "integration and performance"`.

Spec 021: cada línea usa una presentación distinta (una presentación por compra, Historia 8).
"""

from __future__ import annotations

import time

import pytest

from tests.integration.support import PURCHASE, distinct_presentations, draft_body, new_key

pytestmark = [pytest.mark.integration, pytest.mark.performance]


def test_confirmation_of_100_lines_with_real_services(admin, buyer, real_world, sequence) -> None:
    product = real_world.product
    lines = [
        {"company_product_id": product.company_product, "company_product_presentation_id": presentation,
         "quantity": "2", "unit_cost": "900"}
        for presentation in distinct_presentations(admin, real_world, product, 100)
    ]
    samples, parts = [], []
    for _ in range(5):
        draft = buyer.post(f"{PURCHASE}/companies/{real_world.company}/purchases", json=draft_body(real_world, *lines))
        assert draft.status_code == 201, draft.text
        started = time.perf_counter()
        response = buyer.post(
            f"{PURCHASE}/companies/{real_world.company}/purchases/{draft.json()['id']}/confirmation",
            json={"version": draft.json()["version"]},
            headers={"Idempotency-Key": new_key()},
        )
        assert response.status_code == 200, response.text
        confirmed_at = time.perf_counter()
        received = buyer.post(  # spec 020: la recepción es la operación que llama a Inventory
            f"{PURCHASE}/companies/{real_world.company}/purchases/{draft.json()['id']}/receipt",
            json={"version": response.json()["version"], "full_receipt_confirmed": True},
            headers={"Idempotency-Key": new_key()},
        )
        samples.append(time.perf_counter() - started)
        parts.append((round(confirmed_at - started, 3), round(time.perf_counter() - confirmed_at, 3)))
        assert received.status_code == 200, received.text
    worst = max(samples)
    print(f"\nconfirmación y recepción de 100 líneas con servicios reales: máx={worst:.3f}s muestras={[round(s, 3) for s in samples]} (confirmación, recepción)={parts}")
    assert worst <= 3.0
