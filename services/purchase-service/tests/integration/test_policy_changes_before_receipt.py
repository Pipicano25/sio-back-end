"""Cobertura obligatoria al confirmar y cambios de política antes de recibir (spec 021; T100; CP-70, CP-77, CP-79, CP-80).

Ejecutar con `pytest -m integration` en la pila aislada (`SIO_INTEGRATION_CONTAINER_PREFIX=sio-it-`). No detiene
contenedores. Datos ficticios: 10 unidades a 2.000 + 19 % (tasa ficticia) = 23.800 → costo real 2.380.

- CP-70/CP-77: una presentación fuera de toda política bloquea la confirmación (`409`) con CR real; al configurarla,
  el reintento con la misma clave confirma.
- CP-79: la política se retira después de confirmar; la recepción no se bloquea, el inventario entra y CR registra
  `SKIPPED_NO_POLICY` conservando el precio de esa lista (RC-021-13, RC-021-14).
- CP-80: el porcentaje cambia entre la confirmación y la recepción; se aplica el vigente al recibir (RC-021-5).
"""

from __future__ import annotations

import pytest

from tests.integration.support import (
    COMMERCIAL_RELATIONSHIP,
    COVERAGE,
    PRODUCT_CATALOG,
    PURCHASE,
    RUN_ID,
    draft_body,
    new_key,
    wait_until,
)

pytestmark = pytest.mark.integration
CR = COMMERCIAL_RELATIONSHIP


def _ok(response, status=201) -> dict:
    assert response.status_code == status, response.text
    return response.json()


def _uncovered_presentation(admin, world, label: str) -> str:
    """Presentación nueva del producto de prueba **sin** agregarla a la política de cobertura."""
    product = world.product
    global_ = _ok(admin.post(f"{PRODUCT_CATALOG}/products/{product.global_product}/presentations", json={
        "code": f"POL-{label}-{RUN_ID}", "name": f"Presentación ficticia {label} {RUN_ID}", "base_quantity": "1",
        "display_order": 50, "is_base": False,
    }))
    return _ok(admin.post(f"{CR}/companies/{world.company}/company-product-presentations", json={
        "company_product_id": product.company_product, "global_product_presentation_id": global_["id"],
        "sku": f"SKU-POL-{label}-{RUN_ID}",
    }))["id"]


def _line(world, presentation: str) -> dict:
    return {"company_product_id": world.product.company_product, "company_product_presentation_id": presentation,
            "quantity": "10", "unit_cost": "2000"}


def _confirm(buyer, world, draft, key=None):
    return buyer.post(f"{PURCHASE}/companies/{world.company}/purchases/{draft['id']}/confirmation",
                      json={"version": draft["version"]}, headers={"Idempotency-Key": key or new_key()})


def _receive(buyer, world, purchase):
    return buyer.post(f"{PURCHASE}/companies/{world.company}/purchases/{purchase['id']}/receipt",
                      json={"version": purchase["version"], "full_receipt_confirmed": True},
                      headers={"Idempotency-Key": new_key()})


def _policy(admin, world, presentations, markup="30", code=None) -> tuple[str, dict]:
    price_list = _ok(admin.post(f"{CR}/companies/{world.company}/price-lists", json={
        "code": code or f"POL-{new_key()[-8:]}", "name": f"Lista ficticia {RUN_ID}", "currency_code": "COP"}))
    policy = _ok(admin.post(f"{CR}/companies/{world.company}/price-lists/{price_list['id']}/pricing-policies", json={
        "name": f"Política ficticia {RUN_ID}", "markup_percentage": markup, "company_product_presentation_ids": presentations}))
    return price_list["id"], policy


def _applications(admin, world, purchase_id, price_list) -> list[dict]:
    return _ok(admin.get(f"{CR}/companies/{world.company}/automatic-price-applications",
                         params={"purchase_id": purchase_id, "price_list_id": price_list}), 200)["items"]


def _prices(admin, world, price_list, presentation) -> list[dict]:
    items = _ok(admin.get(f"{CR}/companies/{world.company}/price-list-items",
                          params={"price_list_id": price_list, "company_product_presentation_id": presentation,
                                  "status": "ALL"}), 200)["items"]
    return sorted(items, key=lambda item: item["valid_from"])


def test_cp70_cp77_missing_policy_blocks_confirmation_with_real_services(admin, buyer, real_world, sequence) -> None:
    world = real_world
    presentation = _uncovered_presentation(admin, world, "SIN")
    draft = _ok(buyer.post(f"{PURCHASE}/companies/{world.company}/purchases", json=draft_body(world, _line(world, presentation))))
    assert draft["lines"][0]["warnings"] == ["PRICING_POLICY_NOT_CONFIGURED"]
    key = new_key()
    rejected = _confirm(buyer, world, draft, key)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "PURCHASE.PRICING_POLICY_NOT_CONFIGURED"
    assert [error["company_product_presentation_id"] for error in rejected.json()["errors"]] == [presentation]
    current = _ok(buyer.get(f"{PURCHASE}/companies/{world.company}/purchases/{draft['id']}"), 200)
    assert current["status"] == "DRAFT" and current["number"] is None

    _policy(admin, world, [presentation], markup="0")  # 0 % configurado cubre (CP-75)
    confirmed = _confirm(buyer, world, draft, key)
    assert confirmed.status_code == 200, confirmed.text


def test_cp79_policy_removed_after_confirmation_keeps_the_price(admin, buyer, real_world, sequence) -> None:
    world = real_world
    presentation = _uncovered_presentation(admin, world, "RET")
    price_list, policy = _policy(admin, world, [presentation])
    _ok(admin.post(f"{CR}/companies/{world.company}/price-list-items", json={
        "price_list_id": price_list, "company_product_id": world.product.company_product,
        "company_product_presentation_id": presentation, "unit_price": "4100.00", "valid_from": "2026-01-01T00:00:00Z",
    }))
    draft = _ok(buyer.post(f"{PURCHASE}/companies/{world.company}/purchases", json=draft_body(world, _line(world, presentation))))
    confirmed = _ok(_confirm(buyer, world, draft), 200)
    before = _prices(admin, world, price_list, presentation)

    _ok(admin.post(f"{CR}/pricing-policies/{policy['id']}/presentations/remove", json={
        "version": policy["version"], "company_product_presentation_ids": [presentation]}), 200)
    received = _receive(buyer, world, confirmed)
    assert received.status_code == 200, received.text  # la recepción no se bloquea
    assert received.json()["receipt_status"] == "RECEIVED"

    wait_until(lambda: [item["status"] for item in _applications(admin, world, confirmed["id"], price_list)]
               == ["SKIPPED_NO_POLICY"], 90, "CR no registró SKIPPED_NO_POLICY")
    assert _prices(admin, world, price_list, presentation) == before  # 4.100 intacto: importe, vigencias y versión


def test_cp80_percentage_changed_after_confirmation_uses_the_one_at_receipt(admin, buyer, real_world, sequence) -> None:
    world = real_world
    presentation = _uncovered_presentation(admin, world, "PCT")
    price_list, policy = _policy(admin, world, [presentation], markup="30")
    draft = _ok(buyer.post(f"{PURCHASE}/companies/{world.company}/purchases", json=draft_body(world, _line(world, presentation))))
    confirmed = _ok(_confirm(buyer, world, draft), 200)
    _ok(admin.post(f"{CR}/pricing-policies/{policy['id']}/percentage",
                   json={"version": policy["version"], "markup_percentage": "50"}), 200)
    _ok(_receive(buyer, world, confirmed), 200)

    wait_until(lambda: [item["status"] for item in _applications(admin, world, confirmed["id"], price_list)]
               == ["APPLIED"], 90, "CR no aplicó el precio")
    [application] = _applications(admin, world, confirmed["id"], price_list)
    assert application["markup_percentage"] == "50.0000" and application["new_price"] == "3570.00"  # 2.380 × 1,5
    assert COVERAGE[world.company]["list"] != price_list
