"""Commercial Relationship caído durante la recepción y durante la entrega de precios (spec 021, EXC-001; T055).

Ejecutar con `pytest -m integration` en la pila aislada (`SIO_INTEGRATION_CONTAINER_PREFIX=sio-it-`): solo se detienen
contenedores aislados (`support.container` omite la prueba ante uno persistente). Si se interrumpe:
`docker start sio-it-commercial-relationship-service sio-it-purchase-price-update-worker`.

CP-35 distingue dos momentos (decisión del 2026-10-16 sobre el hallazgo H-1; Inventory no cambia):

1. **CR caído durante la recepción.** Inventory valida cada entrada con `POST /company-products/batch-lookup` de CR,
   validación indispensable: la recepción **no** se completa (`503 dependency=inventory`), la operación `RECEIVE`
   queda `PENDING` y recuperable, sin entrada en Inventory, sin serie de costos ni solicitudes de precio. Al volver
   CR, el reintento con la misma clave recibe **una sola vez** y el precio se aplica una sola vez.
2. **CR caído después de la recepción** (durante la actualización de precios). La recepción ya terminó; la solicitud
   queda durablemente en el outbox de Purchase, se reintenta y, al volver CR, el precio se aplica **una sola vez**
   (CP-35, CP-36, SC-002).

Datos ficticios: 10 a 2.000 + 19 % (ficticio) = 23.800 → 3.094.
"""

from __future__ import annotations

import shutil
from decimal import Decimal

import httpx
import pytest

from tests.integration.support import (
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    PURCHASE,
    RUN_ID,
    container,
    docker,
    draft_body,
    new_key,
    unit_line,
    wait_until,
)

pytestmark = pytest.mark.integration

CR_HEALTH = f"{COMMERCIAL_RELATIONSHIP.removesuffix('/api/v1')}/health/ready"


@pytest.fixture(scope="module", autouse=True)
def docker_available():
    if shutil.which("docker") is None:
        pytest.skip("Docker no disponible.")


def _balance(admin, world, product) -> Decimal:
    response = admin.get(f"{INVENTORY}/companies/{world.company}/branches/{world.branch}/balances/{product}")
    if response.status_code == 404:
        return Decimal("0")
    assert response.status_code == 200, response.text
    return Decimal(response.json()["quantity"])


def _automatic_prices(admin, world, price_list) -> list[dict]:
    response = admin.get(
        f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-list-items",
        params={"price_list_id": price_list, "status": "ALL"},
    )
    assert response.status_code == 200, response.text
    return [item for item in response.json()["items"] if item["origin"] == "AUTOMATIC"]


def _automatic_prices_db(world, price_list) -> int:
    """Precios automáticos en la base aislada de CR (la API está caída en ese momento)."""
    out = docker("exec", container("sio-commercial-relationship-db"), "sh", "-c",
                 "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -AtX -c "
                 f"\"SELECT count(*) FROM price_list_items WHERE price_list_id = '{price_list}' AND origin = 'AUTOMATIC'\"")
    return int(out)


def _psql(name: str, sql: str) -> str:
    return docker("exec", container(name), "sh", "-c",
                  f"psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -AtX -F ' ' -c \"{sql}\"")


def _policy_list(admin, world, product, code: str) -> str:
    price_list = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-lists", json={
        "code": code, "name": f"Lista automática ficticia {code}", "currency_code": "COP",
    })
    assert price_list.status_code == 201, price_list.text
    price_list = price_list.json()["id"]
    policy = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-lists/{price_list}/pricing-policies", json={
        "name": f"Política ficticia {code}", "markup_percentage": "30",
        "company_product_presentation_ids": [product.unit_presentation],
    })
    assert policy.status_code == 201, policy.text
    return price_list


def _confirmed(buyer, world, product) -> dict:
    draft = buyer.post(f"{PURCHASE}/companies/{world.company}/purchases",
                       json=draft_body(world, unit_line(product, "10", "2000")))
    assert draft.status_code == 201, draft.text
    assert draft.json()["lines"][0]["total"] == "23800.00"  # 20.000 + 19 % (tasa ficticia)
    confirmed = buyer.post(f"{PURCHASE}/companies/{world.company}/purchases/{draft.json()['id']}/confirmation",
                           json={"version": draft.json()["version"]}, headers={"Idempotency-Key": new_key()})
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()


def _receive(buyer, world, purchase: dict, key: str):
    return buyer.post(
        f"{PURCHASE}/companies/{world.company}/purchases/{purchase['id']}/receipt",
        json={"version": purchase["version"], "full_receipt_confirmed": True},
        headers={"Idempotency-Key": key},
    )


def test_cp35_commercial_relationship_down_during_the_receipt(admin, buyer, real_world, sequence) -> None:
    """CR indispensable para Inventory: la recepción no se completa, queda recuperable y sin efectos duplicados."""
    world, product = real_world, real_world.product
    target = container("sio-commercial-relationship-service")
    price_list = _policy_list(admin, world, product, f"REC{RUN_ID}")
    purchase = _confirmed(buyer, world, product)
    before = _balance(admin, world, product.company_product)
    series_before = _psql("sio-purchase-db", "SELECT coalesce(max(last_sequence), 0) FROM purchase_presentation_cost_series "
                          f"WHERE company_product_presentation_id = '{product.unit_presentation}'")
    key = new_key()

    docker("stop", target)
    try:
        failed = _receive(buyer, world, purchase, key)
        assert failed.status_code == 503, failed.text  # Inventory no pudo validar contra CR
        assert failed.json()["dependency"] == "inventory"
        operation_id = failed.json()["operation_id"]
        again = _receive(buyer, world, purchase, key)  # reintento con CR aún caído: sigue sin efectos
        assert again.status_code == 503 and again.json()["operation_id"] == operation_id, again.text

        current = buyer.get(f"{PURCHASE}/companies/{world.company}/purchases/{purchase['id']}").json()
        assert current["status"] == "CONFIRMED" and current["receipt_status"] == "PENDING"
        assert current["pending_operation_id"] == operation_id  # estado recuperable
        assert _psql("sio-purchase-db", f"SELECT status FROM purchase_operations WHERE id = '{operation_id}'") == "PENDING"
        assert _balance(admin, world, product.company_product) == before  # sin entrada en Inventory
        missing = admin.get(f"{INVENTORY}/companies/{world.company}/inventory-operations/by-key/{operation_id}")
        assert missing.status_code == 404, missing.text
        assert _psql("sio-purchase-db", "SELECT count(*) FROM purchase_price_update_outbox "
                     f"WHERE purchase_id = '{purchase['id']}'") == "0"  # sin solicitudes de precio
        assert _psql("sio-purchase-db", "SELECT coalesce(max(last_sequence), 0) FROM purchase_presentation_cost_series "
                     f"WHERE company_product_presentation_id = '{product.unit_presentation}'") == series_before
    finally:
        docker("start", target)
        wait_until(lambda: httpx.get(CR_HEALTH, timeout=5).status_code == 200, 120, f"{target} no volvió")

    # al volver CR, el reintento con la misma clave completa la misma operación una sola vez
    received = _receive(buyer, world, purchase, key)
    assert received.status_code == 200, received.text
    assert received.json()["receipt_status"] == "RECEIVED"
    inventory_operation = received.json()["inventory_operation_id"]
    replay = _receive(buyer, world, purchase, key)
    assert replay.status_code == 200 and replay.json()["inventory_operation_id"] == inventory_operation
    by_key = admin.get(f"{INVENTORY}/companies/{world.company}/inventory-operations/by-key/{operation_id}")
    assert by_key.status_code == 200 and by_key.json()["id"] == inventory_operation
    assert _balance(admin, world, product.company_product) == before + 10  # una sola entrada
    assert _psql("sio-purchase-db", "SELECT count(*) FROM purchase_price_update_outbox "
                 f"WHERE purchase_id = '{purchase['id']}'") == "1"

    wait_until(lambda: len(_automatic_prices(admin, world, price_list)) == 1, 180,
               "El precio automático no se aplicó tras la recepción recuperada")
    [price] = _automatic_prices(admin, world, price_list)
    assert price["unit_price"] == "3094.00" and price["valid_to"] is None
    applications = admin.get(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/automatic-price-applications",
                             params={"purchase_id": purchase["id"], "price_list_id": price_list})
    assert [item["status"] for item in applications.json()["items"]] == ["APPLIED"]


def test_cp35_cp36_commercial_relationship_down_after_the_receipt(admin, buyer, real_world, sequence) -> None:
    world, product = real_world, real_world.product
    target = container("sio-commercial-relationship-service")
    price_list = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-lists", json={
        "code": f"AUT{RUN_ID}", "name": f"Lista automática ficticia {RUN_ID}", "currency_code": "COP",
    })
    assert price_list.status_code == 201, price_list.text
    price_list = price_list.json()["id"]
    policy = admin.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/price-lists/{price_list}/pricing-policies", json={
        "name": f"Política ficticia {RUN_ID}", "markup_percentage": "30",
        "company_product_presentation_ids": [product.unit_presentation],
    })
    assert policy.status_code == 201, policy.text

    draft = buyer.post(f"{PURCHASE}/companies/{world.company}/purchases",
                       json=draft_body(world, unit_line(product, "10", "2000")))
    assert draft.status_code == 201, draft.text
    assert draft.json()["lines"][0]["total"] == "23800.00"  # 20.000 + 19 % (tasa ficticia)
    confirmed = buyer.post(f"{PURCHASE}/companies/{world.company}/purchases/{draft.json()['id']}/confirmation",
                           json={"version": draft.json()["version"]}, headers={"Idempotency-Key": new_key()})
    assert confirmed.status_code == 200, confirmed.text
    before = _balance(admin, world, product.company_product)

    worker = container("sio-purchase-price-update-worker")
    docker("stop", worker)  # retiene la entrega para que CR caiga antes de recibirla
    try:
        received = buyer.post(
            f"{PURCHASE}/companies/{world.company}/purchases/{confirmed.json()['id']}/receipt",
            json={"version": confirmed.json()["version"], "full_receipt_confirmed": True},
            headers={"Idempotency-Key": new_key()},
        )
        assert received.status_code == 200, received.text  # la recepción no espera al proceso de precios
        assert received.json()["receipt_status"] == "RECEIVED"
        assert _balance(admin, world, product.company_product) == before + 10  # Inventory actualizado
        docker("stop", target)
        docker("start", worker)  # entrega con CR caído: reintentos con espera creciente, sin pérdida

        def outbox() -> list[list[str]]:
            out = docker("exec", container("sio-purchase-db"), "sh", "-c",
                         "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -AtX -F ' ' -c "
                         "\"SELECT purchase_id, status, attempts FROM purchase_price_update_outbox "
                         f"WHERE company_product_presentation_id = '{product.unit_presentation}' ORDER BY sequence\"")
            return [row.split() for row in out.splitlines()]

        def head_retried() -> bool:  # la primera pendiente de la presentación ya falló al menos una vez
            head = next(row for row in outbox() if row[1] == "PENDING")
            return int(head[2]) >= 1

        wait_until(head_retried, 120, "El worker no intentó entregar con CR caído")
        mine = next(row for row in outbox() if row[0] == received.json()["id"])
        assert mine[1] == "PENDING"  # en el outbox: no se pierde con CR caído (las siguientes esperan, orden)
        assert _automatic_prices_db(world, price_list) == 0
    finally:
        docker("start", worker)
        docker("start", target)
        wait_until(lambda: httpx.get(CR_HEALTH, timeout=5).status_code == 200, 120, f"{target} no volvió")

    # CP-36: al volver CR, el precio se aplica (entrega con espera creciente y procesamiento por el worker).
    wait_until(lambda: len(_automatic_prices(admin, world, price_list)) == 1, 180,
               "El precio automático no se aplicó al volver Commercial Relationship")
    [price] = _automatic_prices(admin, world, price_list)
    assert price["unit_price"] == "3094.00" and price["valid_to"] is None

    applications = admin.get(f"{COMMERCIAL_RELATIONSHIP}/companies/{world.company}/automatic-price-applications",
                             params={"purchase_id": confirmed.json()["id"], "price_list_id": price_list})
    assert applications.status_code == 200, applications.text
    [application] = applications.json()["items"]
    assert application["status"] == "APPLIED" and application["new_price"] == "3094.00"
    # una sola vez: los reintentos de entrega no duplican la solicitud ni el precio
    assert len(_automatic_prices(admin, world, price_list)) == 1
