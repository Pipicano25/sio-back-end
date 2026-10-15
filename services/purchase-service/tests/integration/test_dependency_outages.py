"""Dependencias reales detenidas (Principio X, FR-042; SC-003; RC-06; T074).

Ejecutar con `pytest -m integration`. Detiene y vuelve a iniciar contenedores del
entorno aislado (cada uno en un `finally`). Si la prueba se interrumpe: `docker start <contenedor>`.
Solo actúa sobre contenedores aislados (`support.container`: prefijo `SIO_INTEGRATION_CONTAINER_PREFIX` y
etiqueta `sio.integration.isolated=true`); ante un contenedor persistente la prueba se omite.

1. Cada dependencia detenida → `503` con su nombre y sin efectos.
2. Inventory detenido al recibir (spec 020) → operación `PENDING`, compra pendiente de recepción; al
   volver, el reintento con la misma clave recibe una sola vez.
3. Inventory detenido al recibir → al volver, el **conciliador real** (aislado)
   consulta por clave y cierra la operación (`FAILED`, nunca aplicada) sin intervención manual.
"""

from __future__ import annotations

import shutil

import httpx
import pytest

from tests.integration.support import (
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    OPERATIONAL_CONTEXT,
    PARTY_IDENTITY,
    PAYMENT_REFERENCE,
    PRODUCT_CATALOG,
    PURCHASE,
    container,
    docker,
    draft_body,
    new_key,
    unit_line,
    wait_until,
)

pytestmark = pytest.mark.integration

CONTAINERS = {
    "operational-context": ("sio-operational-context-service", f"{OPERATIONAL_CONTEXT.removesuffix('/api/v1')}/health/ready"),
    "commercial-relationship": ("sio-commercial-relationship-service", f"{COMMERCIAL_RELATIONSHIP.removesuffix('/api/v1')}/health/ready"),
    "product-catalog": ("sio-product-catalog-service", f"{PRODUCT_CATALOG.removesuffix('/api/v1')}/health/ready"),
    "party-identity": ("sio-party-identity-service", f"{PARTY_IDENTITY.removesuffix('/api/v1')}/health/ready"),
    "payment-reference": ("sio-payment-reference-service", f"{PAYMENT_REFERENCE}/health/live"),
    "inventory": ("sio-inventory-service", f"{INVENTORY.removesuffix('/api/v1')}/health/ready"),
}


@pytest.fixture(scope="module", autouse=True)
def docker_available():
    if shutil.which("docker") is None:
        pytest.skip("Docker no disponible.")


def stopped(name: str):
    base_name, health = CONTAINERS[name]
    target = container(base_name)

    class _Stopped:
        def __enter__(self):
            docker("stop", target)

        def __exit__(self, *exc):
            docker("start", target)
            wait_until(lambda: httpx.get(health, timeout=5).status_code == 200, 120, f"{target} no volvió")

    return _Stopped()


def url(world, suffix: str = "") -> str:
    return f"{PURCHASE}/companies/{world.company}{suffix}"


def line(world) -> dict:
    return unit_line(world.product_2, "1", "700")


@pytest.mark.parametrize(
    ("dependency", "body_extra"),
    [
        ("operational-context", {}),
        ("commercial-relationship", {}),
        ("product-catalog", {}),
        ("party-identity", {}),
        ("payment-reference", {"supplier_payment_condition_id": None}),
    ],
)
def test_each_dependency_down_is_503_without_effects(buyer, real_world, dependency, body_extra) -> None:
    body = draft_body(real_world, line(real_world))
    if dependency == "payment-reference":
        body["supplier_payment_condition_id"] = real_world.condition
    before = buyer.get(url(real_world, "/purchases")).json()["total_records"]
    with stopped(dependency):
        response = buyer.post(url(real_world, "/purchases"), json=body)
    assert response.status_code == 503, response.text
    assert response.json()["dependency"] == dependency
    assert buyer.get(url(real_world, "/purchases")).json()["total_records"] == before


def confirmed_purchase(buyer, real_world) -> dict:
    """Spec 020: la confirmación es local (no llama a Inventory); la recepción aplica la entrada."""
    draft = buyer.post(url(real_world, "/purchases"), json=draft_body(real_world, line(real_world))).json()
    confirmed = buyer.post(
        url(real_world, f"/purchases/{draft['id']}/confirmation"), json={"version": 1}, headers={"Idempotency-Key": new_key()}
    )
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()


def receipt(buyer, real_world, purchase, key):
    return buyer.post(
        url(real_world, f"/purchases/{purchase['id']}/receipt"),
        json={"version": purchase["version"], "full_receipt_confirmed": True},
        headers={"Idempotency-Key": key},
    )


def test_inventory_down_then_same_key_receives_once(admin, buyer, real_world, sequence) -> None:
    purchase = confirmed_purchase(buyer, real_world)
    key = new_key()
    with stopped("inventory"):
        response = receipt(buyer, real_world, purchase, key)
        assert response.status_code == 503 and response.json()["dependency"] == "inventory"
        operation_id = response.json()["operation_id"]
        current = buyer.get(url(real_world, f"/purchases/{purchase['id']}")).json()
        assert current["receipt_status"] == "PENDING" and current["pending_operation_id"] == operation_id
    retried = receipt(buyer, real_world, purchase, key)
    assert retried.status_code == 200, retried.text
    operation = admin.get(f"{INVENTORY}/companies/{real_world.company}/inventory-operations/by-key/{operation_id}")
    assert operation.status_code == 200 and operation.json()["id"] == retried.json()["inventory_operation_id"]


def test_real_reconciler_closes_pending_operation(buyer, real_world, sequence) -> None:
    purchase = confirmed_purchase(buyer, real_world)
    with stopped("inventory"):
        response = receipt(buyer, real_world, purchase, new_key())
        assert response.status_code == 503
        operation_id = response.json()["operation_id"]
    # Envejece la operación para no esperar el umbral de 300 s; el conciliador corre cada 60 s.
    docker(
        "exec", container("sio-purchase-db"), "sh", "-c",
        "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -c "
        f"\"UPDATE purchase_operations SET updated_at = now() - interval '10 minutes' WHERE id = '{operation_id}'\"",
    )

    def closed() -> bool:
        return buyer.get(f"{PURCHASE}/companies/{real_world.company}/purchase-operations/{operation_id}").json()["status"] != "PENDING"

    wait_until(closed, 150, "El conciliador no cerró la operación PENDING")
    operation = buyer.get(f"{PURCHASE}/companies/{real_world.company}/purchase-operations/{operation_id}").json()
    assert operation["status"] == "FAILED" and operation["error_code"] == "OPERATION_NOT_APPLIED"
    current = buyer.get(url(real_world, f"/purchases/{purchase['id']}")).json()
    assert current["status"] == "CONFIRMED" and current["receipt_status"] == "PENDING"
