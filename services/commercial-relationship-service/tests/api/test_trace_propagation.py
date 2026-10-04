"""Propagación del `trace_id` (R-15, D3, D14)."""

from __future__ import annotations

import logging
from uuid import uuid4

from commercial_relationship_service.observability import current_trace_id
from tests.api.helpers import product_body

TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
TRACEPARENT = f"00-{TRACE}-00f067aa0ba902b7-01"


def test_valid_traceparent_fixes_trace_id_and_reaches_providers(as_user, company, fake_catalog, fake_oc, monkeypatch, caplog):
    seen: list[str | None] = []
    original = fake_catalog.lookup_product

    def spy(product_id):
        seen.append(current_trace_id())
        return original(product_id)

    monkeypatch.setattr(fake_catalog, "lookup_product", spy)
    caplog.set_level(logging.INFO, logger="commercial_relationship_service")
    product = fake_catalog.add(uuid4())

    response = as_user("admin.test").post(
        f"/api/v1/companies/{company}/company-products",
        json=product_body(product),
        headers={"traceparent": TRACEPARENT},
    )

    assert response.status_code == 201, response.text
    assert response.headers["x-trace-id"] == TRACE
    assert seen == [TRACE]


def test_invalid_traceparent_generates_new_trace_id(as_user, company):
    response = as_user("admin.test").get(
        f"/api/v1/companies/{company}/company-products", headers={"traceparent": "garbage"}
    )
    assert response.status_code == 200
    assert len(response.headers["x-trace-id"]) == 32
    assert response.headers["x-trace-id"] != TRACE


def test_trace_id_in_logs(as_user, company, fake_oc, caplog):
    caplog.set_level(logging.WARNING, logger="commercial_relationship_service")
    fake_oc.access_unavailable = True
    response = as_user("admin.test").get(
        f"/api/v1/companies/{company}/company-products", headers={"traceparent": TRACEPARENT}
    )
    assert response.status_code == 503
    assert any(getattr(record, "trace_id", None) == TRACE for record in caplog.records)
