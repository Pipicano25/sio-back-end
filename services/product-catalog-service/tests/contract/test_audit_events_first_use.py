"""Evento del primer uso (feature 016; acciones PC 62–63; DS-10; T059).

`REGISTER_PRODUCT_FIRST_USE` con `origin` AUTOMATIC (adopción desde Commercial Relationship, autor
técnico) o MANUAL (administrador); si el primer uso ya estaba registrado, no hay otro evento.
"""

from __future__ import annotations

from tests import factories
from tests.contract.test_audit_events_simple_catalogs import check


def _url(product_id, manual: bool = False) -> str:
    return f"/api/v1/products/{product_id}/first-use" + ("/manual" if manual else "")


def test_automatic_first_use_by_technical_consumer(api_as, session_factory, outbox, clear_outbox) -> None:
    consumer = api_as("first-use:register", sub="9a8b7c6d-0000-4000-8000-000000000001")
    product, _, _ = factories.complete_product(session_factory)
    box = factories.presentation(session_factory, product.id, "CAJA", base_quantity=20)
    clear_outbox()

    first = consumer.post(_url(product.id), json={"global_product_presentation_id": str(box.id)})
    assert first.status_code == 200, first.text
    again = consumer.post(_url(product.id), json={"global_product_presentation_id": str(box.id)})
    assert again.status_code == 200

    (event,) = outbox()  # la repetición no registra otro evento
    check(event, "REGISTER_PRODUCT_FIRST_USE", "Product", str(product.id))
    assert event["new_values"]["origin"] == "AUTOMATIC"
    assert event["keycloak_user_id"] == "9a8b7c6d-0000-4000-8000-000000000001"


def test_manual_first_use(api, session_factory, outbox, clear_outbox) -> None:
    product, _, _ = factories.complete_product(session_factory)
    clear_outbox()

    response = api.post(_url(product.id, manual=True))
    assert response.status_code == 200, response.text
    again = api.post(_url(product.id, manual=True))
    assert again.status_code in (200, 409)

    (event,) = outbox()
    check(event, "REGISTER_PRODUCT_FIRST_USE", "Product", str(product.id))
    assert event["new_values"]["origin"] == "MANUAL"
