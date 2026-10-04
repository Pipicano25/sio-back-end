"""Altas simultáneas de la misma identidad como cliente (RC-04)."""

from __future__ import annotations

import threading
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import ApiClient


def test_two_simultaneous_customers_with_the_same_identity(app, user_token, company, fake_party):
    person = uuid4()
    fake_party.persons[person] = "ACTIVE"
    barrier = threading.Barrier(2)
    results = []

    def run(code):
        with TestClient(app, raise_server_exceptions=False) as client:
            barrier.wait()
            results.append(
                ApiClient(client, user_token("admin.test")).post(
                    f"/api/v1/companies/{company}/company-customers",
                    json={"customer_kind": "PERSON", "person_identity_id": str(person),
                          "internal_code": code, "display_name": "Cliente"},
                )
            )

    threads = [threading.Thread(target=run, args=(code,)) for code in ("A", "B")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(r.status_code for r in results) == [201, 409], [r.text for r in results]
    conflict = next(r for r in results if r.status_code == 409)
    assert conflict.json()["code"] == "COMMERCIAL_RELATIONSHIP.DUPLICATE_CUSTOMER"
