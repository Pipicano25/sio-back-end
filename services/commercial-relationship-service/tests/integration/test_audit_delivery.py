"""Entrega real de la auditoría de Commercial Relationship (feature 016; SC-007; RC-04; T042).

Exige el entorno integrado con `commercial-relationship-audit-outbox-worker`,
`product-catalog-audit-outbox-worker` y Audit en ejecución. Datos ficticios de validación.
"""

from __future__ import annotations

import os
import time

import pytest

from tests.integration.test_real_dependencies import (  # noqa: F401 (fixtures)
    _first_id,
    _organization,
    COMMERCIAL_RELATIONSHIP,
    PRODUCT_CATALOG,
    RUN_ID,
    client,
    colombia,
    company_id,
    organization_id,
    person_id,
)

pytestmark = pytest.mark.integration

AUDIT = os.environ.get("AUDIT_SERVICE_BASE_URL", "http://127.0.0.1:8110/api/v1").rstrip("/")
CR_SERVICE_ACCOUNT = "4d586bde-69d8-4f30-b05a-50b4ec68f72f"


@pytest.fixture(scope="module")
def adopted_product(client, company_id):
    """Producto global nuevo adoptado en la empresa, con códigos propios de este módulo.

    No reutiliza la fixture de `test_real_dependencies`: al ser de módulo se ejecutaría dos veces con el
    mismo `RUN_ID` en una sola corrida y la segunda categoría respondería `409`.
    """
    unit = _first_id(client, f"{PRODUCT_CATALOG}/units-of-measure", status="ACTIVE")
    category = client.post(f"{PRODUCT_CATALOG}/categories", json={
        "code": f"AUD-CRB-{RUN_ID}", "name": f"Categoría ficticia de auditoría CR {RUN_ID}",
    })
    assert category.status_code == 201, category.text
    product = client.post(f"{PRODUCT_CATALOG}/products", json={
        "product_type": "GOOD", "canonical_name": f"Producto ficticio de auditoría CR {RUN_ID}", "base_unit_id": unit,
    })
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    assert client.post(f"{PRODUCT_CATALOG}/products/{product_id}/categories",
                       json={"global_category_id": category.json()["id"]}).status_code == 201
    presentation = client.post(f"{PRODUCT_CATALOG}/products/{product_id}/presentations", json={
        "code": f"AJ-{RUN_ID}", "name": "Caja (dato ficticio)", "is_base": True,
    })
    assert presentation.status_code == 201, presentation.text
    adopted = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-products", json={
        "global_product_id": product_id, "internal_code": f"AUDB-{RUN_ID}",
        "display_name": f"Producto ficticio de auditoría {RUN_ID}", "currency_code": "COP",
    })
    assert adopted.status_code == 201, adopted.text
    return {"global_product_id": product_id, "company_product": adopted.json()}


def _items(response) -> list[dict]:
    return response.json()["items"] if response.status_code == 200 else []


def _company_history(client, company: str, entity_type: str, entity_id: str) -> list[dict]:
    return _items(client.get(f"{AUDIT}/companies/{company}/entity-history/{entity_type}/{entity_id}", params={"page_size": 100}))


def _platform_history(client, entity_type: str, entity_id: str) -> list[dict]:
    return _items(client.get(f"{AUDIT}/platform-entity-history/{entity_type}/{entity_id}", params={"page_size": 100}))


def _wait(read, actions: list[str], timeout: float = 120) -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        items = read()
        if all(any(item["action"] == action for item in items) for action in actions):
            return items
        time.sleep(2)
    pytest.fail(f"Audit no recibió {actions}.")


def test_commercial_history_reaches_audit_once(client, company_id, adopted_product, colombia) -> None:
    product = adopted_product["company_product"]
    supplier_org_id = _organization(client, colombia, "AUD ")
    supplier = client.post(f"{COMMERCIAL_RELATIONSHIP}/companies/{company_id}/company-suppliers", json={
        "organization_identity_id": supplier_org_id, "internal_code": f"AUD-{RUN_ID}",
        "display_name": "Proveedor de auditoría (dato ficticio)",
    })
    assert supplier.status_code == 201, supplier.text
    blocked = client.post(f"{COMMERCIAL_RELATIONSHIP}/company-suppliers/{supplier.json()['id']}/block",
                          json={"version": supplier.json()["version"], "block_reason": "Validación de auditoría"})
    assert blocked.status_code == 200, blocked.text

    supplier_events = _wait(lambda: _company_history(client, company_id, "CompanySupplier", supplier.json()["id"]),
                            ["CREATE_COMPANY_SUPPLIER", "BLOCK_COMPANY_SUPPLIER"])
    product_events = _wait(lambda: _company_history(client, company_id, "CompanyProduct", product["id"]),
                           ["ADOPT_COMPANY_PRODUCT"])
    first_use = _wait(lambda: _platform_history(client, "Product", adopted_product["global_product_id"]),
                      ["REGISTER_PRODUCT_FIRST_USE"])
    time.sleep(5)

    assert [e["action"] for e in _company_history(client, company_id, "CompanySupplier", supplier.json()["id"])] == [
        "CREATE_COMPANY_SUPPLIER", "BLOCK_COMPANY_SUPPLIER",
    ]  # una sola entrega por evento, ordenada por occurred_at
    assert {e["source_service"] for e in supplier_events + product_events} == {"commercial-relationship-service"}
    block = supplier_events[-1]
    assert block["reason"] == "Validación de auditoría" and block["new_values"]["status"] == "BLOCKED"
    use = next(e for e in first_use if e["action"] == "REGISTER_PRODUCT_FIRST_USE")
    assert use["source_service"] == "product-catalog-service" and use["company_id"] is None
    assert use["keycloak_user_id"] == CR_SERVICE_ACCOUNT and use["new_values"]["origin"] == "AUTOMATIC"
