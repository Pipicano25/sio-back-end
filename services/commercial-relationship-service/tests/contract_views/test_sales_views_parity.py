"""Paridad de las vistas de contrato de Commercial Relationship para Sales (spec 025, T035).

Para los mismos datos, cada columna de la vista coincide con el mismo campo de la respuesta que hoy lee Sales:

- ``v1_company_products`` ↔ ``company-products/batch-lookup`` (y ``GET /company-products/{id}`` para
  ``reference_code`` y ``created_at``, que el lote no devuelve) y el conteo de ``GET /companies/{c}/company-products``;
- ``v1_company_product_presentations`` ↔ ``company-product-presentations/batch-lookup`` y ``by-products``;
- ``v1_company_customers`` ↔ ``GET /company-customers/{id}`` y la búsqueda por identidad de Sales
  (``GET /companies/{c}/company-customers?status=ALL&customer_kind=...&<identidad>=...``);
- ``v1_price_lists`` ↔ ``GET /price-lists/{id}``.

Incluye filas inactivas y de otra empresa: la vista tiene todas las empresas y el consumidor filtra por
``company_id``; filtrar la vista por ``company_id`` da lo mismo que el endpoint de esa empresa.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.api.helpers import (
    adopt,
    adopt_presentation,
    create_price_list,
    organization_customer,
    person_customer,
)
from tests.conftest import LOOKUP, user_sub

PRODUCT_COLUMNS = (
    "id", "company_id", "global_product_id", "internal_code", "reference_code", "display_name", "status",
    "is_sellable", "is_purchasable", "inventory_control_enabled", "purchase_tax_percentage", "created_at",
)
PRODUCT_BATCH_COLUMNS = tuple(column for column in PRODUCT_COLUMNS if column not in ("reference_code", "created_at"))
PRESENTATION_COLUMNS = (
    "id", "company_id", "company_product_id", "global_product_presentation_id", "internal_code", "sku",
    "reference_code", "is_sellable", "is_purchasable", "status",
)
CUSTOMER_COLUMNS = (
    "id", "company_id", "customer_kind", "person_identity_id", "organization_identity_id", "display_name", "status",
)
PRICE_LIST_COLUMNS = ("id", "company_id", "status")


def _norm(column: str, value: Any) -> Any:
    """Lleva el valor de la vista y el de la respuesta JSON a la misma forma."""
    if value is None or isinstance(value, bool):
        return value
    if column == "purchase_tax_percentage":
        return Decimal(str(value))
    if column == "created_at":
        return value if isinstance(value, datetime) else datetime.fromisoformat(value)
    return str(value)


def _assert_same(view: dict[str, Any], body: dict[str, Any], columns: tuple[str, ...]) -> None:
    for column in columns:
        assert _norm(column, view[column]) == _norm(column, body[column]), column


def _view_rows(connection, view: str, ids: list[str]) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        text(f"SELECT * FROM contract.{view} WHERE id = ANY(CAST(:ids AS uuid[]))"), {"ids": ids}
    ).mappings().all()
    return {str(row["id"]): dict(row) for row in rows}


@pytest.fixture
def admin(as_user, fake_oc, other_company):
    """`admin.test`, miembro de las dos empresas para poder preparar datos en ambas."""
    fake_oc.add_member(user_sub("admin.test"), other_company)
    return as_user("admin.test")


@pytest.fixture
def technical(as_token, service_token):
    """Identidad técnica de Sales: lectura de cada recurso con `platform:lookup` (sin membresía)."""
    return as_token(service_token(
        "perm:commercial-relationship:company_products:read",
        "perm:commercial-relationship:company_product_presentations:read",
        "perm:commercial-relationship:company_customers:read",
        "perm:commercial-relationship:price_lists:read",
        LOOKUP,
        client_id="sales-service",
    ))


def _deactivate(client, path: str) -> dict[str, Any]:
    version = client.get(path).json()["version"]
    response = client.post(f"{path}/deactivate", json={"version": version})
    assert response.status_code == 200, response.text
    return response.json()


def test_company_products_and_presentations_match_batch_lookup(
    admin, technical, company, other_company, fake_catalog, test_engine
):
    plain = adopt(admin, company, fake_catalog, internal_code="P-1", reference_code="REF-1")
    taxed = adopt(admin, company, fake_catalog, internal_code="P-2", is_purchasable=False,
                  inventory_control_enabled=False)
    response = admin.put(f"/api/v1/company-products/{taxed['id']}/purchase-tax",
                         json={"version": taxed["version"], "purchase_tax_percentage": "19.5"})
    assert response.status_code == 200, response.text
    closed = adopt(admin, company, fake_catalog, internal_code="P-3")
    foreign = adopt(admin, other_company, fake_catalog, internal_code="P-1")

    presentations = [
        adopt_presentation(admin, company, fake_catalog, plain, sku="SKU-1", internal_code="PP-1",
                           reference_code="R-1"),
        adopt_presentation(admin, company, fake_catalog, plain, is_sellable=False),
        adopt_presentation(admin, company, fake_catalog, taxed, sku="SKU-2"),
        adopt_presentation(admin, company, fake_catalog, closed),
        adopt_presentation(admin, other_company, fake_catalog, foreign, sku="SKU-1"),
    ]
    _deactivate(admin, f"/api/v1/company-product-presentations/{presentations[1]['id']}")
    _deactivate(admin, f"/api/v1/company-products/{closed['id']}")

    product_ids = [item["id"] for item in (plain, taxed, closed, foreign)]
    presentation_ids = [item["id"] for item in presentations]
    batch = technical.post("/api/v1/company-products/batch-lookup", json={"ids": [*product_ids, str(uuid4())]})
    assert batch.status_code == 200, batch.text
    presentation_batch = technical.post("/api/v1/company-product-presentations/batch-lookup",
                                        json={"ids": [*presentation_ids, str(uuid4())]})
    assert presentation_batch.status_code == 200, presentation_batch.text

    with test_engine.connect() as connection:
        products = _view_rows(connection, "v1_company_products", [item["id"] for item in batch.json()["items"]])
        found = [item for item in batch.json()["items"] if item["found"]]
        assert sorted(products) == sorted(item["id"] for item in found) == sorted(product_ids)
        assert {products[item["id"]]["status"] for item in found} == {"ACTIVE", "INACTIVE"}
        for item in found:
            _assert_same(products[item["id"]], item, PRODUCT_BATCH_COLUMNS)
            body = admin.get(f"/api/v1/company-products/{item['id']}").json()
            _assert_same(products[item["id"]], body, PRODUCT_COLUMNS)
        assert products[taxed["id"]]["purchase_tax_percentage"] == Decimal("19.5")

        views = _view_rows(connection, "v1_company_product_presentations",
                           [item["id"] for item in presentation_batch.json()["items"]])
        found = [item for item in presentation_batch.json()["items"] if item["found"]]
        assert sorted(views) == sorted(item["id"] for item in found) == sorted(presentation_ids)
        for item in found:
            _assert_same(views[item["id"]], item, PRESENTATION_COLUMNS)

        # El consumidor filtra por empresa: la vista filtrada coincide con el listado y con `by-products`.
        for company_id in (company, other_company):
            for status in ("ACTIVE", "INACTIVE", "ALL"):
                listed = admin.get(f"/api/v1/companies/{company_id}/company-products",
                                   params={"status": status, "page_size": 100}).json()
                counted = connection.execute(
                    text("SELECT count(*) FROM contract.v1_company_products "
                         "WHERE company_id = :c AND (:s = 'ALL' OR status = :s)"),
                    {"c": company_id, "s": status},
                ).scalar_one()
                assert counted == listed["total_records"], (company_id, status)

            by_products = admin.post(
                f"/api/v1/companies/{company_id}/company-product-presentations/by-products",
                json={"company_product_ids": product_ids, "status": "ALL"},
            )
            assert by_products.status_code == 200, by_products.text
            rows = connection.execute(
                text("SELECT * FROM contract.v1_company_product_presentations "
                     "WHERE company_id = :c AND company_product_id = ANY(CAST(:ids AS uuid[])) "
                     "ORDER BY company_product_id, id"),
                {"c": company_id, "ids": product_ids},
            ).mappings().all()
            items = by_products.json()["items"]
            assert [str(row["id"]) for row in rows] == [item["id"] for item in items]
            for row, item in zip(rows, items, strict=True):
                _assert_same(dict(row), item, PRESENTATION_COLUMNS)


def test_company_customers_match_get_and_identity_search(
    admin, technical, as_user, company, other_company, fake_party, test_engine
):
    person = person_customer(admin, company, fake_party, internal_code="C-1", display_name="Ana Pérez")
    inactive_person = person_customer(admin, company, fake_party, internal_code="C-2")
    _deactivate(admin, f"/api/v1/company-customers/{inactive_person['id']}")
    organization = organization_customer(admin, company, fake_party, internal_code="C-3")
    # La misma persona es cliente de otra empresa, con otro nombre.
    response = admin.post(
        f"/api/v1/companies/{other_company}/company-customers",
        json={"customer_kind": "PERSON", "person_identity_id": person["person_identity_id"],
              "internal_code": "C-1", "display_name": "Ana en otra"},
    )
    assert response.status_code == 201, response.text
    foreign = response.json()

    customers = (person, inactive_person, organization, foreign)
    with test_engine.connect() as connection:
        views = _view_rows(connection, "v1_company_customers", [item["id"] for item in customers])
        assert sorted(views) == sorted(item["id"] for item in customers)
        for customer in customers:
            response = technical.get(f"/api/v1/company-customers/{customer['id']}")
            assert response.status_code == 200, response.text
            _assert_same(views[customer["id"]], response.json(), CUSTOMER_COLUMNS)
        assert views[inactive_person["id"]]["status"] == "INACTIVE"

        # Búsqueda por identidad con el token del vendedor, exactamente como `customer_registry.find` de Sales.
        seller = as_user("ventas.test")
        searches = (
            ("PERSON", "person_identity_id",
             [person["person_identity_id"], inactive_person["person_identity_id"], foreign["person_identity_id"],
              str(uuid4())]),
            ("ORGANIZATION", "organization_identity_id", [organization["organization_identity_id"], str(uuid4())]),
        )
        for kind, field, identities in searches:
            response = seller.get(
                f"/api/v1/companies/{company}/company-customers",
                params={"status": "ALL", "customer_kind": kind, field: identities, "page_size": "100"},
            )
            assert response.status_code == 200, response.text
            rows = connection.execute(
                text(f"SELECT * FROM contract.v1_company_customers WHERE company_id = :c AND customer_kind = :k "
                     f"AND {field} = ANY(CAST(:ids AS uuid[]))"),
                {"c": company, "k": kind, "ids": identities},
            ).mappings().all()
            items = {item["id"]: item for item in response.json()["items"]}
            assert sorted(str(row["id"]) for row in rows) == sorted(items), kind
            for row in rows:
                _assert_same(dict(row), items[str(row["id"])], CUSTOMER_COLUMNS)


def test_price_lists_match_get(admin, technical, company, other_company, test_engine):
    active = create_price_list(admin, company)
    inactive = create_price_list(admin, company)
    _deactivate(admin, f"/api/v1/price-lists/{inactive['id']}")
    foreign = create_price_list(admin, other_company)

    lists = (active, inactive, foreign)
    with test_engine.connect() as connection:
        views = _view_rows(connection, "v1_price_lists", [item["id"] for item in lists])
        assert sorted(views) == sorted(item["id"] for item in lists)
        for price_list in lists:
            response = technical.get(f"/api/v1/price-lists/{price_list['id']}")
            assert response.status_code == 200, response.text
            _assert_same(views[price_list["id"]], response.json(), PRICE_LIST_COLUMNS)
        assert views[inactive["id"]]["status"] == "INACTIVE"
        assert str(views[foreign["id"]]["company_id"]) == str(other_company)
