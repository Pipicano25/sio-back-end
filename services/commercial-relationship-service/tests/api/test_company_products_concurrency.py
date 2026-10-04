"""Adopciones simultáneas (RC-04, RC-05, SC-005).

Dos solicitudes pasan la unicidad local a la vez; ambas registran el primer uso
(idempotente en Product Catalog) y la base garantiza que solo una se guarda.
"""

from __future__ import annotations

import threading
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.api.helpers import product_body
from tests.conftest import ApiClient


def _race(app, token, company, bodies):
    barrier = threading.Barrier(len(bodies))
    results = []

    def run(body):
        with TestClient(app, raise_server_exceptions=False) as client:
            barrier.wait()
            response = ApiClient(client, token).post(
                f"/api/v1/companies/{company}/company-products", json=body
            )
            results.append(response)

    threads = [threading.Thread(target=run, args=(body,)) for body in bodies]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def test_two_simultaneous_adoptions_of_the_same_product(app, user_token, company, fake_catalog, as_user):
    product = fake_catalog.add(uuid4())
    bodies = [product_body(product, internal_code=f"C-{index}") for index in range(2)]

    results = _race(app, user_token("admin.test"), company, bodies)

    statuses = sorted(response.status_code for response in results)
    assert statuses == [201, 409], [r.text for r in results]
    conflict = next(r for r in results if r.status_code == 409)
    assert conflict.json()["code"] == "COMMERCIAL_RELATIONSHIP.DUPLICATE_ADOPTION"
    assert fake_catalog.first_use_calls.count(product) == 2  # ambas marcaron el primer uso

    listing = as_user("admin.test").get(
        f"/api/v1/companies/{company}/company-products", params={"status": "ALL"}
    )
    assert listing.json()["total_records"] == 1


def test_two_simultaneous_adoptions_with_the_same_code(app, user_token, company, fake_catalog):
    bodies = [product_body(fake_catalog.add(uuid4()), internal_code="MISMO") for _ in range(2)]

    results = _race(app, user_token("admin.test"), company, bodies)

    assert sorted(response.status_code for response in results) == [201, 409]
    conflict = next(r for r in results if r.status_code == 409)
    assert conflict.json()["code"] == "COMMERCIAL_RELATIONSHIP.DUPLICATE_INTERNAL_CODE"
