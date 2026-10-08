"""Dependencias reales detenidas (Principio X, FR-030; RC-06; T080).

Ejecutar con `pytest -m integration`. Detiene y vuelve a iniciar contenedores compartidos del
entorno integrado (cada uno en un `finally`). Si la prueba se interrumpe: `docker start <contenedor>`.

1. Cada dependencia detenida → `503` con su nombre y sin efectos.
2. Inventory detenido al confirmar → operación `PENDING`, venta en borrador; al volver, el reintento
   con la misma clave confirma una sola vez.
3. Inventory detenido al confirmar → al volver, el **conciliador real** (`sio-sales-reconciler`)
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
    PRODUCT_CATALOG,
    SALES,
    docker,
    draft_body,
    new_key,
    wait_until,
)

pytestmark = pytest.mark.integration

CONTAINERS = {
    "operational-context": ("sio-operational-context-service", f"{OPERATIONAL_CONTEXT.removesuffix('/api/v1')}/health/ready"),
    "commercial-relationship": ("sio-commercial-relationship-service", f"{COMMERCIAL_RELATIONSHIP.removesuffix('/api/v1')}/health/ready"),
    "product-catalog": ("sio-product-catalog-service", f"{PRODUCT_CATALOG.removesuffix('/api/v1')}/health/ready"),
    "party-identity": ("sio-party-identity-service", f"{PARTY_IDENTITY.removesuffix('/api/v1')}/health/ready"),
    "inventory": ("sio-inventory-service", f"{INVENTORY.removesuffix('/api/v1')}/health/ready"),
}


@pytest.fixture(scope="module", autouse=True)
def docker_available():
    if shutil.which("docker") is None:
        pytest.skip("Docker no disponible.")


def stopped(name: str):
    container, health = CONTAINERS[name]

    class _Stopped:
        def __enter__(self):
            docker("stop", container)

        def __exit__(self, *exc):
            docker("start", container)
            wait_until(lambda: httpx.get(health, timeout=5).status_code == 200, 120, f"{container} no volvió")

    return _Stopped()


def url(world, suffix: str = "") -> str:
    return f"{SALES}/companies/{world.company}{suffix}"


def line(world) -> dict:
    return {"company_product_id": world.product_2.company_product, "quantity": "1"}


@pytest.mark.parametrize(
    ("dependency", "body_extra"),
    [
        ("operational-context", {}),
        ("commercial-relationship", {}),
        ("product-catalog", {}),
        ("party-identity", {}),
    ],
)
def test_each_dependency_down_is_503_without_effects(seller, real_world, dependency, body_extra) -> None:
    body = draft_body(real_world, line(real_world))
    before = seller.get(url(real_world, "/sales")).json()["total_records"]
    with stopped(dependency):
        response = seller.post(url(real_world, "/sales"), json=body)
    assert response.status_code == 503, response.text
    assert response.json()["dependency"] == dependency
    assert seller.get(url(real_world, "/sales")).json()["total_records"] == before


def test_inventory_down_then_same_key_confirms_once(admin, seller, real_world, sequence) -> None:
    draft = seller.post(url(real_world, "/sales"), json=draft_body(real_world, line(real_world))).json()
    key = new_key()
    with stopped("inventory"):
        response = seller.post(url(real_world, f"/sales/{draft['id']}/confirmation"), json={"version": 1}, headers={"Idempotency-Key": key})
        assert response.status_code == 503 and response.json()["dependency"] == "inventory"
        operation_id = response.json()["operation_id"]
        current = seller.get(url(real_world, f"/sales/{draft['id']}")).json()
        assert current["status"] == "DRAFT" and current["number"] is None and current["pending_operation_id"] == operation_id
    retried = seller.post(url(real_world, f"/sales/{draft['id']}/confirmation"), json={"version": 1}, headers={"Idempotency-Key": key})
    assert retried.status_code == 200, retried.text
    operation = admin.get(f"{INVENTORY}/companies/{real_world.company}/inventory-operations/by-key/{operation_id}")
    assert operation.status_code == 200 and operation.json()["id"] == retried.json()["inventory_operation_id"]


def test_real_reconciler_closes_pending_operation(seller, real_world, sequence) -> None:
    draft = seller.post(url(real_world, "/sales"), json=draft_body(real_world, line(real_world))).json()
    with stopped("inventory"):
        response = seller.post(
            url(real_world, f"/sales/{draft['id']}/confirmation"), json={"version": 1}, headers={"Idempotency-Key": new_key()}
        )
        assert response.status_code == 503
        operation_id = response.json()["operation_id"]
    # Envejece la operación para no esperar el umbral de 300 s; el conciliador corre cada 60 s.
    docker(
        "exec", "sio-sales-db", "sh", "-c",
        "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -c "
        f"\"UPDATE sale_operations SET updated_at = now() - interval '10 minutes' WHERE id = '{operation_id}'\"",
    )

    def closed() -> bool:
        return seller.get(f"{SALES}/companies/{real_world.company}/sale-operations/{operation_id}").json()["status"] != "PENDING"

    wait_until(closed, 150, "El conciliador no cerró la operación PENDING")
    operation = seller.get(f"{SALES}/companies/{real_world.company}/sale-operations/{operation_id}").json()
    assert operation["status"] == "FAILED" and operation["error_code"] == "OPERATION_NOT_APPLIED"
    assert seller.get(url(real_world, f"/sales/{draft['id']}")).json()["status"] == "DRAFT"
