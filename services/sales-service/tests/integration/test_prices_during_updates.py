"""Ventas mientras se actualizan los precios (spec 021; T061; CP-40, CP-41, CP-42).

Ejecutar con `pytest -m integration` en la pila aislada (`SIO_INTEGRATION_CONTAINER_PREFIX=sio-it-`). Detiene solo el
contenedor aislado `sio-it-commercial-relationship-price-worker` para dejar una actualización pendiente; si la prueba
se interrumpe: `docker start sio-it-commercial-relationship-price-worker`. Datos ficticios: 10 unidades a 1.000 + 19 %
(tasa ficticia) = 11.900 → 1.190 por unidad; con 30 % el precio automático es 1.547.
"""

from __future__ import annotations

import shutil

import pytest

from tests.integration.support import (
    COMMERCIAL_RELATIONSHIP,
    RUN_ID,
    SALES,
    adopt_product,
    container,
    docker,
    draft_body,
    new_key,
    stock_with_purchase,
    wait_until,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def docker_available():
    if shutil.which("docker") is None:
        pytest.skip("Docker no disponible.")


def _draft(seller, world, product, price_list) -> dict:
    response = seller.post(f"{SALES}/companies/{world.company}/sales", json=draft_body(world, {
        "company_product_id": product.company_product, "company_product_presentation_id": product.unit_presentation,
        "quantity": "1", "price_list_id": price_list,
    }))
    assert response.status_code == 201, response.text
    return response.json()


def _confirm(seller, world, sale):
    return seller.post(f"{SALES}/companies/{world.company}/sales/{sale['id']}/confirmation",
                       json={"version": sale["version"]}, headers={"Idempotency-Key": new_key()})


def _applications(admin, world, purchase_id, price_list) -> list[dict]:
    """Las de la lista de la prueba: otras listas con política de la empresa también reciben una aplicación (B-3)."""
    response = admin.get(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/automatic-price-applications",
                         params={"purchase_id": purchase_id, "price_list_id": price_list})
    assert response.status_code == 200, response.text
    return response.json()["items"]


def test_cp40_cp42_sales_use_the_current_price_while_an_update_is_pending(admin, seller, real_world, sequence) -> None:
    world = real_world
    product = adopt_product(admin, world, f"PDU{RUN_ID}")
    price_list = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-lists", json={
        "code": f"PDU{RUN_ID}", "name": f"Lista ficticia con política {RUN_ID}", "currency_code": "COP",
        "valid_from": "2026-01-01T00:00:00Z",
    })
    assert price_list.status_code == 201, price_list.text
    price_list = price_list.json()["id"]
    manual = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-list-items", json={
        "price_list_id": price_list, "company_product_id": product.company_product,
        "company_product_presentation_id": product.unit_presentation, "unit_price": "1700.00",
        "valid_from": "2026-01-01T00:00:00Z",
    })
    assert manual.status_code == 201, manual.text
    policy = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-lists/{price_list}/pricing-policies", json={
        "name": f"Política ficticia {RUN_ID}", "markup_percentage": "30",
        "company_product_presentation_ids": [product.unit_presentation],
    })
    assert policy.status_code == 201, policy.text

    worker = container("sio-commercial-relationship-price-worker")
    docker("stop", worker)
    try:
        received = stock_with_purchase(admin, world, [(product, "10", "1000")])
        # Purchase entrega la solicitud; sin worker de precios la actualización queda pendiente en CR
        wait_until(lambda: [item["status"] for item in _applications(admin, world, received["id"], price_list)] == ["PENDING"], 90,
                   "La solicitud no llegó a Commercial Relationship")

        # CP-40: se vende con el último precio vigente (el manual) mientras la actualización está pendiente
        first = _draft(seller, world, product, price_list)
        assert first["lines"][0]["unit_price"] == "1700.0000"
        assert _confirm(seller, world, first).status_code == 200
        second = _draft(seller, world, product, price_list)
        assert second["lines"][0]["unit_price"] == "1700.0000"
    finally:
        docker("start", worker)

    wait_until(lambda: [item["status"] for item in _applications(admin, world, received["id"], price_list)] == ["APPLIED"], 90,
               "El worker de precios no procesó la actualización pendiente")

    # CP-42: el precio cambió entre el borrador y la confirmación → 409 PRICES_CHANGED (Sales no cambia)
    response = _confirm(seller, world, second)
    assert response.status_code == 409 and response.json()["code"] == "SALES.PRICES_CHANGED", response.text
    change = response.json()["errors"][0]
    assert (change["stored"]["unit_price"], change["current"]["unit_price"]) == ("1700.0000", "1547.0000")

    # al completarse, las ventas nuevas usan el precio nuevo
    third = _draft(seller, world, product, price_list)
    assert third["lines"][0]["unit_price"] == "1547.0000"
    assert _confirm(seller, world, third).status_code == 200


def test_cp41_without_a_current_price_the_line_is_rejected(admin, seller, real_world) -> None:
    world = real_world
    product = adopt_product(admin, world, f"SINP{RUN_ID}")
    price_list = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-lists", json={
        "code": f"SINP{RUN_ID}", "name": f"Lista ficticia sin precio {RUN_ID}", "currency_code": "COP",
        "valid_from": "2026-01-01T00:00:00Z",
    })
    assert price_list.status_code == 201, price_list.text
    policy = admin.post(
        f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-lists/{price_list.json()['id']}/pricing-policies",
        json={"name": f"Política ficticia {RUN_ID}", "markup_percentage": "30",
              "company_product_presentation_ids": [product.unit_presentation]},
    )
    assert policy.status_code == 201, policy.text  # con política pero aún sin recepción: no hay precio
    response = seller.post(f"{SALES}/companies/{world.company}/sales", json=draft_body(world, {
        "company_product_id": product.company_product, "company_product_presentation_id": product.unit_presentation,
        "quantity": "1", "price_list_id": price_list.json()["id"],
    }))
    assert response.status_code == 409, response.text
    codes = {error["code"] for error in response.json().get("errors", [])}
    assert codes & {"PRICE_NOT_IN_LIST", "PRICE_NOT_AVAILABLE"}, response.text
