"""Confirmación de 100 líneas con servicios reales (SC-001; T077). `pytest -m "integration and performance"`."""

from __future__ import annotations

import time

import pytest

from tests.integration.support import PURCHASE, draft_body, new_key

pytestmark = [pytest.mark.integration, pytest.mark.performance]


def test_confirmation_of_100_lines_with_real_services(buyer, real_world, sequence) -> None:
    lines = [
        {
            "company_product_id": (real_world.product if index % 2 else real_world.product_2).company_product,
            "quantity": "2",
            "unit_cost": "900",
        }
        for index in range(100)
    ]
    samples = []
    for _ in range(5):
        draft = buyer.post(f"{PURCHASE}/companies/{real_world.company}/purchases", json=draft_body(real_world, *lines))
        assert draft.status_code == 201, draft.text
        started = time.perf_counter()
        response = buyer.post(
            f"{PURCHASE}/companies/{real_world.company}/purchases/{draft.json()['id']}/confirmation",
            json={"version": draft.json()["version"]},
            headers={"Idempotency-Key": new_key()},
        )
        samples.append(time.perf_counter() - started)
        assert response.status_code == 200, response.text
    worst = max(samples)
    print(f"\nconfirmación de 100 líneas con servicios reales: máx={worst:.3f}s muestras={[round(s, 3) for s in samples]}")
    assert worst <= 3.0
