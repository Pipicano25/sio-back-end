"""Vía técnica de solo lectura en el listado `GET /companies/{c}/company-products` (spec 022, decisión del 2026-10-17).

`product-inventory-query-service` cuenta los productos adoptados con `total_records` del listado. El listado acepta,
como CR-1, una cuenta de servicio con `perm:commercial-relationship:platform:lookup` **y**
`perm:commercial-relationship:company_products:read`; la autorización de los miembros no cambia, nunca se admite el
acceso anónimo y la exención no se aplica a escrituras ni a usuarios humanos.
"""

from __future__ import annotations

from uuid import uuid4

from tests.api.helpers import adopt
from tests.conftest import LOOKUP

URL = "/api/v1/companies/{company}/company-products"
READ = "perm:commercial-relationship:company_products:read"
CREATE = "perm:commercial-relationship:company_products:create"
CLIENT = "product-inventory-query-service"
ADOPTED = {"status": "ACTIVE", "inventory_control_enabled": "true", "page_size": 1}


def seed(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    adopt(client, company, fake_catalog, internal_code="A1", inventory_control_enabled=True)
    adopt(client, company, fake_catalog, internal_code="A2", inventory_control_enabled=True)
    adopt(client, company, fake_catalog, internal_code="S1", inventory_control_enabled=False)
    inactive = adopt(client, company, fake_catalog, internal_code="I1", inventory_control_enabled=True)
    deactivated = client.post(f"/api/v1/company-products/{inactive['id']}/deactivate", json={"version": inactive["version"]})
    assert deactivated.status_code == 200, deactivated.text


def test_member_user_is_still_authorized(as_user, company, fake_catalog) -> None:
    """Caso 1: un usuario miembro con el permiso sigue leyendo el listado (sin cambios)."""
    seed(as_user, company, fake_catalog)
    response = as_user("admin.test").get(URL.format(company=company), params=ADOPTED)
    assert response.status_code == 200 and response.json()["total_records"] == 2


def test_technical_account_with_both_permissions_counts_adopted_products(as_user, as_token, service_token, company,
                                                                         fake_catalog) -> None:
    """Caso 2: con `platform:lookup` y `company_products:read`, mismo resultado y mismos filtros que un miembro.

    `adopted_products` (spec 022, FR-022-55): `ACTIVE` y con control de inventario; excluye el inactivo y el
    producto sin control.
    """
    seed(as_user, company, fake_catalog)
    technical = as_token(service_token(READ, LOOKUP, client_id=CLIENT))
    response = technical.get(URL.format(company=company), params=ADOPTED)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_records"] == 2 and len(body["items"]) == 1
    assert set(body) == {"items", "page", "page_size", "total_records", "total_pages"}  # contrato sin cambios
    member = as_user("admin.test").get(URL.format(company=company), params=ADOPTED).json()
    assert body == member


def test_technical_account_without_platform_lookup_is_not_a_member(as_token, service_token, company) -> None:
    """Caso 3: sin `platform:lookup` la cuenta técnica no tiene membresía: `404`."""
    response = as_token(service_token(READ, client_id=CLIENT)).get(URL.format(company=company), params=ADOPTED)
    assert response.status_code == 404


def test_technical_account_without_read_permission_is_forbidden(as_token, service_token, company) -> None:
    """Caso 4: sin `company_products:read`, `403` aunque tenga `platform:lookup`."""
    response = as_token(service_token(LOOKUP, client_id=CLIENT)).get(URL.format(company=company), params=ADOPTED)
    assert response.status_code == 403 and "perm:" not in response.text


def test_no_membership_no_technical_identity_and_anonymous(as_user, as_token, make_token, company, other_company) -> None:
    """Caso 5: usuario sin membresía `404`; un humano con `platform:lookup` no obtiene la exención; anónimo `401`."""
    assert as_user("admin.test").get(URL.format(company=other_company)).status_code == 404
    human_with_lookup = as_token(make_token(READ, LOOKUP, sub="humano-con-lookup", preferred_username="humano"))
    assert human_with_lookup.get(URL.format(company=company)).status_code == 404
    assert as_token(None).get(URL.format(company=company)).status_code == 401


def test_technical_exemption_does_not_open_writes(as_token, service_token, company, fake_catalog) -> None:
    """La vía técnica es solo de lectura: adoptar con `platform:lookup` y `create` sigue exigiendo membresía."""
    product = fake_catalog.add(uuid4())
    technical = as_token(service_token(READ, CREATE, LOOKUP, client_id=CLIENT))
    response = technical.post(URL.format(company=company), json={
        "global_product_id": str(product), "internal_code": "TEC-W", "display_name": "Escritura técnica",
        "currency_code": "COP", "inventory_control_enabled": True})
    assert response.status_code == 404
