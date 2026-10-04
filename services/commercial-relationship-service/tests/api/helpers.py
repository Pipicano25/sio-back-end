"""Ayudas comunes de las pruebas de API: cuerpos válidos y altas de preparación."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4


def product_body(global_product_id: UUID, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "global_product_id": str(global_product_id),
        "internal_code": "000045",
        "display_name": "Acetaminofén 500 mg caja x100",
        "currency_code": "COP",
    }
    body.update(overrides)
    return body


def product_update_body(current: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    keys = (
        "internal_code",
        "reference_code",
        "display_name",
        "short_name",
        "sale_price",
        "currency_code",
        "reference_cost",
        "inventory_control_enabled",
        "lot_tracking_enabled",
        "expiration_tracking_enabled",
        "is_purchasable",
        "is_sellable",
        "version",
    )
    body = {key: current[key] for key in keys}
    body.update(overrides)
    return body


def adopt(client, company_id: UUID, fake_catalog, **overrides: Any) -> dict[str, Any]:
    """Adopta un producto global nuevo y elegible; devuelve la representación."""
    product = fake_catalog.add(uuid4())
    response = client.post(
        f"/api/v1/companies/{company_id}/company-products",
        json=product_body(product, **overrides),
    )
    assert response.status_code == 201, response.text
    return response.json()


def person_customer(client, company_id: UUID, fake_party, **overrides: Any) -> dict[str, Any]:
    person = uuid4()
    fake_party.persons[person] = "ACTIVE"
    body = {
        "customer_kind": "PERSON",
        "person_identity_id": str(person),
        "internal_code": overrides.pop("internal_code", "CLI-001"),
        "display_name": overrides.pop("display_name", "Cliente ficticio de validación"),
        **overrides,
    }
    response = client.post(f"/api/v1/companies/{company_id}/company-customers", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def organization_customer(client, company_id: UUID, fake_party, **overrides: Any) -> dict[str, Any]:
    organization = uuid4()
    fake_party.organizations[organization] = "ACTIVE"
    body = {
        "customer_kind": "ORGANIZATION",
        "organization_identity_id": str(organization),
        "internal_code": overrides.pop("internal_code", "CLI-ORG-001"),
        "display_name": overrides.pop("display_name", "Organización cliente ficticia"),
        **overrides,
    }
    response = client.post(f"/api/v1/companies/{company_id}/company-customers", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def supplier(client, company_id: UUID, fake_party, **overrides: Any) -> dict[str, Any]:
    organization = overrides.pop("organization_identity_id", None) or uuid4()
    fake_party.organizations[UUID(str(organization))] = "ACTIVE"
    body = {
        "organization_identity_id": str(organization),
        "internal_code": overrides.pop("internal_code", "PRV-001"),
        "display_name": overrides.pop("display_name", "Proveedor ficticio de validación"),
        **overrides,
    }
    response = client.post(f"/api/v1/companies/{company_id}/company-suppliers", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def code_of(response) -> str:
    return response.json()["code"].removeprefix("COMMERCIAL_RELATIONSHIP.")
