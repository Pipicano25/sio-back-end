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
        "currency_code",
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


# --------------------------------------------------------------------------
# Fase B (specs/010-commercial-relationship-commercial-product)
# --------------------------------------------------------------------------


def global_presentation(fake_catalog, product: dict[str, Any], **kwargs: Any) -> UUID:
    """Presentación global `ACTIVE` y elegible del producto global del producto empresarial."""
    return fake_catalog.add_presentation(uuid4(), UUID(product["global_product_id"]), **kwargs)


def adopt_presentation(client, company_id: UUID, fake_catalog, product: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    """Adopta una presentación global nueva para el producto empresarial; devuelve la representación."""
    body = {
        "company_product_id": product["id"],
        "global_product_presentation_id": str(global_presentation(fake_catalog, product)),
        **overrides,
    }
    response = client.post(f"/api/v1/companies/{company_id}/company-product-presentations", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def presentation_update_body(current: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    keys = (
        "internal_code", "sku", "reference_code", "is_purchasable", "is_sellable",
        "is_default_purchase", "is_default_sale", "version",
    )
    return {**{key: current[key] for key in keys}, **overrides}


def supplier_product_body(supplier_row: dict[str, Any], product: dict[str, Any], fake_catalog, **overrides: Any) -> dict[str, Any]:
    body = {
        "company_supplier_id": supplier_row["id"],
        "company_product_id": product["id"],
        "purchase_unit_id": str(fake_catalog.base_units[UUID(product["global_product_id"])]),
        "currency_code": "COP",
    }
    body.update(overrides)
    return body


def create_supplier_product(client, company_id: UUID, supplier_row, product, fake_catalog, **overrides: Any) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/companies/{company_id}/supplier-products",
        json=supplier_product_body(supplier_row, product, fake_catalog, **overrides),
    )
    assert response.status_code == 201, response.text
    return response.json()


def supplier_product_update_body(current: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    keys = (
        "company_product_presentation_id", "supplier_product_code", "purchase_unit_id",
        "minimum_order_quantity", "pack_quantity", "negotiated_unit_cost", "currency_code",
        "expected_supplier_lead_time_hours", "priority", "is_preferred", "version",
    )
    return {**{key: current[key] for key in keys}, **overrides}


def create_condition(client, company_id: UUID, supplier_row, fake_payment, code: str = "CREDIT", **overrides: Any) -> dict[str, Any]:
    body = {
        "company_supplier_id": supplier_row["id"],
        "payment_condition_type_id": str(fake_payment.id_of(code)),
        "currency_code": "COP",
        "payment_terms_days": 0 if code == "CASH" else 30,
        **overrides,
    }
    response = client.post(f"/api/v1/companies/{company_id}/supplier-payment-conditions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def condition_update_body(current: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    keys = (
        "payment_condition_type_id", "currency_code", "payment_terms_days", "credit_limit",
        "interest_rate_percentage", "cash_discount_percentage", "is_default", "valid_from",
        "valid_to", "version",
    )
    return {**{key: current[key] for key in keys}, **overrides}


def create_price_list(client, company_id: UUID, **overrides: Any) -> dict[str, Any]:
    body = {"code": overrides.pop("code", f"L-{uuid4().hex[:6]}"), "name": "Minorista", "currency_code": "COP", **overrides}
    response = client.post(f"/api/v1/companies/{company_id}/price-lists", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def price_list_update_body(current: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    keys = ("code", "name", "description", "valid_from", "valid_to", "is_default", "version")
    return {**{key: current[key] for key in keys}, **overrides}


def sellable_presentation(client, company_id: UUID, product: dict[str, Any], fake_catalog=None) -> str:
    """Presentación vendible del producto (spec 019: todo precio es de una presentación).

    Usa la primera adoptada `ACTIVE` y vendible; si no hay y se pasa `fake_catalog`, adopta una.
    """
    listed = client.get(
        f"/api/v1/companies/{company_id}/company-product-presentations", params={"company_product_id": product["id"]}
    )
    assert listed.status_code == 200, listed.text
    for item in listed.json()["items"]:
        if item["status"] == "ACTIVE" and item["is_sellable"]:
            return item["id"]
    assert fake_catalog is not None, "El producto no tiene presentación vendible: pase fake_catalog (spec 019)"
    return adopt_presentation(client, company_id, fake_catalog, product)["id"]


def create_price(client, company_id: UUID, price_list: dict[str, Any], product: dict[str, Any], fake_catalog=None,
                 **overrides: Any) -> dict[str, Any]:
    """Precio de una presentación (spec 019); sin `company_product_presentation_id` usa una vendible del producto."""
    if "company_product_presentation_id" not in overrides:
        overrides["company_product_presentation_id"] = sellable_presentation(client, company_id, product, fake_catalog)
    body = {"price_list_id": price_list["id"], "company_product_id": product["id"], "unit_price": "15000.00", **overrides}
    response = client.post(f"/api/v1/companies/{company_id}/price-list-items", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def price_update_body(current: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    keys = ("unit_price", "valid_from", "valid_to", "version")
    return {**{key: current[key] for key in keys}, **overrides}
