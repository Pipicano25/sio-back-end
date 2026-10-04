"""Historia 2: modificar productos empresariales (FR-015, DS-07, DS-17, RC-09)."""

from __future__ import annotations

from uuid import uuid4

from tests.api.helpers import adopt, code_of, product_body, product_update_body
from tests.conftest import user_sub


def _put(client, product, **overrides):
    return client.put(
        f"/api/v1/company-products/{product['id']}", json=product_update_body(product, **overrides)
    )


def test_update_all_fields(as_user, company, fake_catalog):
    product = adopt(as_user("admin.test"), company, fake_catalog)
    lookups = len(fake_catalog.lookup_calls)

    response = _put(
        as_user("supervisor.test"),
        product,
        display_name="Nuevo nombre",
        short_name="Corto",
        reference_code="REF-9",
        sale_price="18900",
        reference_cost="1000.5",
        is_sellable=False,
        lot_tracking_enabled=True,
        expiration_tracking_enabled=True,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == product["version"] + 1
    assert body["display_name"] == "Nuevo nombre" and body["is_sellable"] is False
    assert body["sale_price"] == "18900.00" and body["reference_cost"] == "1000.5000"
    assert body["updated_by"] == user_sub("supervisor.test")
    assert body["created_by"] == product["created_by"]
    assert body["status"] == "ACTIVE"
    assert len(fake_catalog.lookup_calls) == lookups  # el PUT no consulta Product Catalog


def test_identical_put_does_not_bump_version(as_user, company, fake_catalog):
    product = adopt(as_user("admin.test"), company, fake_catalog)
    response = _put(as_user("admin.test"), product)
    assert response.status_code == 200
    assert response.json()["version"] == product["version"]
    assert response.json()["updated_at"] == product["updated_at"]


def test_stale_version_is_409(as_user, company, fake_catalog):
    product = adopt(as_user("admin.test"), company, fake_catalog)
    assert _put(as_user("admin.test"), product, display_name="v2").status_code == 200
    response = _put(as_user("admin.test"), product, display_name="v3")
    assert response.status_code == 409
    assert code_of(response) == "VERSION_CONFLICT"


def test_immutable_fields(as_user, company, fake_catalog):
    product = adopt(as_user("admin.test"), company, fake_catalog)

    for field, value in (
        ("global_product_id", product["global_product_id"]),
        ("company_id", product["company_id"]),
        ("status", "INACTIVE"),
    ):
        body = product_update_body(product)
        body[field] = value
        response = as_user("admin.test").put(f"/api/v1/company-products/{product['id']}", json=body)
        assert response.status_code == 422, field
        assert code_of(response) == "IMMUTABLE_FIELD"


def test_internal_code_changes(as_user, company, fake_catalog):
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog, internal_code="abc-1")
    adopt(client, company, fake_catalog, internal_code="OTRO")

    same = _put(client, product, internal_code="ABC-1")
    assert same.status_code == 200
    assert same.json()["internal_code"] == "ABC-1"

    taken = _put(client, same.json(), internal_code="otro")
    assert taken.status_code == 409
    assert code_of(taken) == "DUPLICATE_INTERNAL_CODE"


def test_currency_change_revalidates_price_scale(as_user, company, fake_catalog):
    product = adopt(as_user("admin.test"), company, fake_catalog, sale_price="1500.50")
    response = _put(as_user("admin.test"), product, currency_code="CLP")
    assert response.status_code == 422
    assert code_of(response) == "PRICE_SCALE_NOT_ALLOWED"

    response = _put(as_user("admin.test"), product, currency_code="CLP", sale_price="1500")
    assert response.status_code == 200
    assert response.json()["sale_price"] == "1500.00"


def test_invalid_flags_on_update(as_user, company, fake_catalog):
    product = adopt(as_user("admin.test"), company, fake_catalog)
    response = _put(as_user("admin.test"), product, inventory_control_enabled=False, lot_tracking_enabled=True)
    assert code_of(response) == "INVENTORY_FLAGS_INVALID"


def test_read_only_user_cannot_update(as_user, company, fake_catalog):
    product = adopt(as_user("admin.test"), company, fake_catalog)
    assert _put(as_user("compras.test"), product, display_name="x").status_code == 403


def test_inactive_company_blocks_put_in_any_state(as_user, company, fake_catalog, fake_oc):
    client = as_user("admin.test")
    active = adopt(client, company, fake_catalog)
    other = adopt(client, company, fake_catalog, internal_code="INACT")
    inactive = client.post(f"/api/v1/company-products/{other['id']}/deactivate", json={"version": 1}).json()

    fake_oc.inactive_companies.add(company)

    for product in (active, inactive):
        response = _put(client, product, display_name="cambio")
        assert response.status_code == 422
        assert code_of(response) == "COMPANY_INACTIVE"


def test_put_on_inactive_product_keeps_status(as_user, company, fake_catalog):
    """DS-17: el PUT se permite sobre INACTIVE y no reactiva."""
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog, internal_code="VIEJO")
    inactive = client.post(f"/api/v1/company-products/{product['id']}/deactivate", json={"version": 1}).json()

    response = _put(client, inactive, display_name="Corregido")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "INACTIVE"
    assert body["version"] == inactive["version"] + 1
    assert body["updated_by"] == user_sub("admin.test")

    immutable = product_update_body(body)
    immutable["global_product_id"] = body["global_product_id"]
    assert code_of(client.put(f"/api/v1/company-products/{product['id']}", json=immutable)) == "IMMUTABLE_FIELD"


def test_changing_code_of_inactive_product_releases_it(as_user, company, fake_catalog):
    """Flujo de reutilización del código interno (DS-17, RN-13)."""
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog, internal_code="000045")
    inactive = client.post(f"/api/v1/company-products/{product['id']}/deactivate", json={"version": 1}).json()

    # Inactivar no libera el código.
    new_product = fake_catalog.add(uuid4())
    blocked = client.post(
        f"/api/v1/companies/{company}/company-products", json=product_body(new_product, internal_code="000045")
    )
    assert blocked.status_code == 409
    assert code_of(blocked) == "DUPLICATE_INTERNAL_CODE"

    assert _put(client, inactive, internal_code="000045-OLD").status_code == 200

    adopt_attempt = client.post(
        f"/api/v1/companies/{company}/company-products", json=product_body(new_product, internal_code="000045")
    )
    assert adopt_attempt.status_code == 201
