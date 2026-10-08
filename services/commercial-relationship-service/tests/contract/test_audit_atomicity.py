"""Rechazos sin evento y atomicidad cambio + outbox en CR (feature 016; DS-02, RC-01, RC-06; T038)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.api.helpers import adopt, product_body, product_update_body


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


def test_rejections_record_no_event(admin, as_user, as_token, company, other_company, fake_catalog, outbox) -> None:
    product = adopt(admin, company, fake_catalog)
    before = len(outbox())
    url = f"/api/v1/company-products/{product['id']}"

    assert as_token(None).put(url, json=product_update_body(product, display_name="X")).status_code == 401
    assert as_user("consulta.test").put(url, json=product_update_body(product, display_name="X")).status_code == 403
    assert admin.put(url, json=product_update_body(product, display_name="X", version=99)).status_code == 409
    assert admin.put(url, json=product_update_body(product, currency_code="XX")).status_code == 422
    duplicated = admin.post(
        f"/api/v1/companies/{company}/company-products",
        json=product_body(product["global_product_id"], internal_code="OTRO-01"),
    )
    assert duplicated.status_code == 409
    assert admin.post(f"/api/v1/companies/{other_company}/company-products",
                      json=product_body(product["global_product_id"])).status_code in (403, 404)

    assert len(outbox()) == before


def test_failure_after_recording_rolls_back_change_and_event(admin, company, fake_catalog, outbox) -> None:
    product = adopt(admin, company, fake_catalog)
    before = len(outbox())

    with patch(
        "commercial_relationship_service.application.audit_events.record_audit_event",
        side_effect=RuntimeError("fallo simulado al escribir la outbox"),
    ):
        response = admin.put(
            f"/api/v1/company-products/{product['id']}", json=product_update_body(product, display_name="No se guarda"),
        )

    assert response.status_code == 500
    assert len(outbox()) == before
    current = admin.get(f"/api/v1/company-products/{product['id']}").json()
    assert current["display_name"] == product["display_name"] and current["version"] == product["version"]


def test_responses_are_unchanged_by_auditing(admin, company, fake_catalog) -> None:
    product = adopt(admin, company, fake_catalog)

    response = admin.put(f"/api/v1/company-products/{product['id']}", json=product_update_body(product, display_name="Y"))

    assert response.status_code == 200 and set(response.json()) == set(product)
