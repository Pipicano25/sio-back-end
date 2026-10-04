"""Historia 2: inactivar y reactivar productos empresariales (FR-016; RC-08, RC-09, RC-10)."""

from __future__ import annotations

from uuid import UUID

from tests.api.helpers import adopt, code_of


def _action(client, product, action, version=None):
    return client.post(
        f"/api/v1/company-products/{product['id']}/{action}",
        json={"version": version if version is not None else product["version"]},
    )


def test_deactivate_requires_delete_permission(as_user, company, fake_catalog):
    product = adopt(as_user("admin.test"), company, fake_catalog)
    assert _action(as_user("supervisor.test"), product, "deactivate").status_code == 403

    response = _action(as_user("admin.test"), product, "deactivate")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "INACTIVE" and body["version"] == 2

    # Sigue consultable por UUID.
    assert as_user("compras.test").get(f"/api/v1/company-products/{product['id']}").status_code == 200


def test_repeated_deactivate_is_409_without_version_change(as_user, company, fake_catalog):
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog)
    inactive = _action(client, product, "deactivate").json()

    response = _action(client, inactive, "deactivate")
    assert response.status_code == 409
    assert code_of(response) == "INVALID_STATUS_TRANSITION"
    assert client.get(f"/api/v1/company-products/{product['id']}").json()["version"] == inactive["version"]


def test_deactivate_allowed_with_inactive_company(as_user, company, fake_catalog, fake_oc):
    product = adopt(as_user("admin.test"), company, fake_catalog)
    fake_oc.inactive_companies.add(company)
    assert _action(as_user("admin.test"), product, "deactivate").status_code == 200


def test_reactivate_without_first_use_or_completeness(as_user, company, fake_catalog):
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog)
    inactive = _action(client, product, "deactivate").json()
    # El producto global quedó incompleto: la reactivación no exige completitud.
    product_id = UUID(product["global_product_id"])
    fake_catalog.add(product_id, eligible=False)
    first_uses = len(fake_catalog.first_use_calls)

    response = _action(as_user("supervisor.test"), inactive, "reactivate")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ACTIVE"
    assert len(fake_catalog.first_use_calls) == first_uses
    assert fake_catalog.lookup_calls[-1] == product_id


def test_reactivate_rejections(as_user, company, fake_catalog):
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog)
    inactive = _action(client, product, "deactivate").json()
    global_id = UUID(product["global_product_id"])

    fake_catalog.add(global_id, status="INACTIVE")
    response = _action(client, inactive, "reactivate")
    assert response.status_code == 422 and code_of(response) == "GLOBAL_PRODUCT_INACTIVE"

    del fake_catalog.products[global_id]
    response = _action(client, inactive, "reactivate")
    assert code_of(response) == "GLOBAL_PRODUCT_NOT_FOUND"

    fake_catalog.lookup_unavailable = True
    response = _action(client, inactive, "reactivate")
    assert response.status_code == 503


def test_reactivate_with_inactive_company_and_stale_version(as_user, company, fake_catalog, fake_oc):
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog)
    inactive = _action(client, product, "deactivate").json()

    assert code_of(_action(client, inactive, "reactivate", version=1)) == "VERSION_CONFLICT"

    fake_oc.inactive_companies.add(company)
    response = _action(client, inactive, "reactivate")
    assert response.status_code == 422 and code_of(response) == "COMPANY_INACTIVE"


def test_reactivate_active_is_invalid_transition(as_user, company, fake_catalog):
    product = adopt(as_user("admin.test"), company, fake_catalog)
    response = _action(as_user("admin.test"), product, "reactivate")
    assert response.status_code == 409
    assert code_of(response) == "INVALID_STATUS_TRANSITION"


def test_no_delete_route(as_user, company, fake_catalog):
    product = adopt(as_user("admin.test"), company, fake_catalog)
    response = as_user("admin.test").request("DELETE", f"/api/v1/company-products/{product['id']}")
    assert response.status_code == 405
