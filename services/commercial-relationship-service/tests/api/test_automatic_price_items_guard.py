"""Historia 3 de la spec 021: los precios cerrados o cancelados automáticamente no reviven (T049; FR-021-24, 25).

CP-25 (reactivar la lista no revive precios cerrados ni cancelados), CP-52 (`reactivate` → `409`), CP-T17 (un `PUT` que
extiende la vigencia de un precio cerrado → `409`), CP-67 (las respuestas de precios no exponen costos ni porcentajes).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tests.api.automatic_pricing_helpers import (
    current_price,
    policy,
    prices,
    request_body,
    run_worker,
    scenario,
    submit,
    technical,
)
from tests.api.helpers import code_of, create_price, price_update_body


@pytest.fixture
def supervisor(as_user):
    return as_user("supervisor.test")


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


def _processed(supervisor, as_token, service_token, company, fake_catalog, test_engine):
    """Precio manual vigente + futuro, y una recepción con política: el vigente se cierra y el futuro se cancela."""
    world = scenario(supervisor, company, fake_catalog)
    start = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    manual = create_price(supervisor, company, world.price_list, world.product,
                          company_product_presentation_id=world.presentation, unit_price="3500.00",
                          valid_to=start)
    future = create_price(supervisor, company, world.price_list, world.product,
                          company_product_presentation_id=world.presentation, unit_price="3600.00",
                          valid_from=start)
    policy(supervisor, world, [world.presentation], markup="30")
    submit(technical(as_token, service_token), world, request_body(world))
    run_worker(test_engine)
    return world, manual, future


def test_cp52_cancelled_future_price_cannot_be_reactivated(supervisor, as_token, service_token, company, fake_catalog, test_engine) -> None:
    world, _, future = _processed(supervisor, as_token, service_token, company, fake_catalog, test_engine)
    current = supervisor.get(f"/api/v1/price-list-items/{future['id']}").json()
    assert current["status"] == "INACTIVE" and current["closure_reason"] == "AUTOMATIC_SUPERSEDED"
    response = supervisor.post(f"/api/v1/price-list-items/{future['id']}/reactivate", json={"version": current["version"]})
    assert response.status_code == 409 and code_of(response) == "PRICE_CLOSED_BY_AUTOMATIC_UPDATE"


def test_cpt17_closed_price_cannot_be_extended(supervisor, as_token, service_token, company, fake_catalog, test_engine) -> None:
    world, manual, _ = _processed(supervisor, as_token, service_token, company, fake_catalog, test_engine)
    current = supervisor.get(f"/api/v1/price-list-items/{manual['id']}").json()
    assert current["valid_to"] is not None and current["closure_reason"] == "AUTOMATIC_SUPERSEDED"
    response = supervisor.put(f"/api/v1/price-list-items/{manual['id']}", json=price_update_body(current, valid_to=None))
    assert response.status_code == 409 and code_of(response) == "PRICE_CLOSED_BY_AUTOMATIC_UPDATE"


def test_cp25_reactivating_the_list_does_not_revive_closed_prices(admin, supervisor, as_token, service_token, company, fake_catalog, test_engine) -> None:
    world, manual, future = _processed(supervisor, as_token, service_token, company, fake_catalog, test_engine)
    listed = admin.get(f"/api/v1/price-lists/{world.price_list['id']}").json()
    assert admin.post(f"/api/v1/price-lists/{world.price_list['id']}/deactivate", json={"version": listed["version"]}).status_code == 200
    listed = admin.get(f"/api/v1/price-lists/{world.price_list['id']}").json()
    assert admin.post(f"/api/v1/price-lists/{world.price_list['id']}/reactivate", json={"version": listed["version"]}).status_code == 200
    rows = {str(row["id"]): row for row in prices(test_engine, world)}
    assert rows[manual["id"]]["valid_to"] is not None  # sigue cerrado
    assert rows[future["id"]]["status"] == "INACTIVE"  # sigue cancelado
    assert str(current_price(test_engine, world)) == "3094.0000"  # rige el automático


def test_cp67_price_responses_expose_origin_but_no_costs(supervisor, as_user, as_token, service_token, company, fake_catalog, test_engine) -> None:
    world, _, _ = _processed(supervisor, as_token, service_token, company, fake_catalog, test_engine)
    seller = as_user("ventas.test")
    items = seller.get(f"/api/v1/companies/{company}/price-list-items",
                       params={"price_list_id": world.price_list["id"], "status": "ALL"}).json()["items"]
    automatic = next(item for item in items if item["origin"] == "AUTOMATIC")
    assert automatic["automatic_application_id"] and automatic["closure_reason"] is None
    forbidden = ("cost", "markup", "policy", "reference")
    assert not any(word in key for item in items for key in item for word in forbidden)
    resolved = seller.post(f"/api/v1/companies/{company}/applicable-prices/resolve", json={"lines": [{
        "line_id": "1", "company_product_id": world.product["id"],
        "company_product_presentation_id": world.presentation, "price_list_id": world.price_list["id"],
    }]})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["items"][0]["unit_price"] == "3094.00"
    assert not any(word in str(resolved.json()) for word in ("cost", "markup", "policy"))
