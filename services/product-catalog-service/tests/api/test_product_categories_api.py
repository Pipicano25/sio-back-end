"""Clasificación del producto en categorías (RC-04, FR-024, FR-031, FR-034 a FR-037, FR-006)."""

from tests import factories


def _url(product_id) -> str:
    return f"/api/v1/products/{product_id}/categories"


def _setup(session_factory):
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id)
    parent = factories.category(session_factory, "GRANOS")
    child = factories.category(session_factory, "ARROZ", parent=parent.id)
    return product, parent, child


def test_first_category_becomes_primary(api, session_factory) -> None:
    product, _, arroz = _setup(session_factory)

    response = api.post(_url(product.id), json={"global_category_id": str(arroz.id)})

    assert response.status_code == 201
    assert response.json()["is_primary"] is True


def test_non_leaf_category_can_be_assigned(api, session_factory) -> None:
    product, granos, _ = _setup(session_factory)
    assert api.post(_url(product.id), json={"global_category_id": str(granos.id)}).status_code == 201


def test_set_primary_switches_atomically(api, session_factory) -> None:
    product, granos, arroz = _setup(session_factory)
    first = api.post(_url(product.id), json={"global_category_id": str(arroz.id)}).json()
    second = api.post(_url(product.id), json={"global_category_id": str(granos.id)}).json()
    assert second["is_primary"] is False

    items = api.post(f"{_url(product.id)}/{second['id']}/set-primary", json={"version": 1}).json()

    primaries = {item["id"]: item["is_primary"] for item in items}
    assert primaries == {first["id"]: False, second["id"]: True}


def test_removing_primary_requires_new_primary(api, session_factory) -> None:
    product, granos, arroz = _setup(session_factory)
    first = api.post(_url(product.id), json={"global_category_id": str(arroz.id)}).json()
    second = api.post(_url(product.id), json={"global_category_id": str(granos.id)}).json()

    missing = api.post(f"{_url(product.id)}/{first['id']}/deactivate", json={"version": 1})
    assert missing.json()["code"] == "PRODUCT_CATALOG.NEW_PRIMARY_REQUIRED"

    done = api.post(
        f"{_url(product.id)}/{first['id']}/deactivate",
        json={"version": 1, "new_primary_association_id": second["id"]},
    )
    assert done.status_code == 200
    items = {item["id"]: item for item in api.get(_url(product.id)).json()}
    assert items[second["id"]]["is_primary"] is True
    assert items[first["id"]]["status"] == "INACTIVE"


def test_removing_only_category_leaves_product_incomplete(api, session_factory) -> None:
    product, _, arroz = _setup(session_factory)
    only = api.post(_url(product.id), json={"global_category_id": str(arroz.id)}).json()

    assert api.post(f"{_url(product.id)}/{only['id']}/deactivate", json={"version": 1}).status_code == 200
    issues = api.get(f"/api/v1/products/{product.id}/completeness").json()["issues"]
    assert "NO_ACTIVE_CATEGORY" in issues


def test_reassigning_inactive_pair_reactivates_without_restoring_primary(api, session_factory) -> None:
    product, granos, arroz = _setup(session_factory)
    first = api.post(_url(product.id), json={"global_category_id": str(arroz.id)}).json()
    second = api.post(_url(product.id), json={"global_category_id": str(granos.id)}).json()
    api.post(
        f"{_url(product.id)}/{first['id']}/deactivate",
        json={"version": 1, "new_primary_association_id": second["id"]},
    )

    again = api.post(_url(product.id), json={"global_category_id": str(arroz.id)})

    assert again.status_code == 200
    assert again.json()["id"] == first["id"]
    assert again.json()["status"] == "ACTIVE"
    assert again.json()["is_primary"] is False


def test_duplicate_and_inactive_category(api, session_factory) -> None:
    product, granos, arroz = _setup(session_factory)
    api.post(_url(product.id), json={"global_category_id": str(arroz.id)})

    duplicate = api.post(_url(product.id), json={"global_category_id": str(arroz.id)})
    assert duplicate.json()["code"] == "PRODUCT_CATALOG.DUPLICATE_ASSOCIATION"

    inactive = factories.category(session_factory, "VIEJA", status="INACTIVE")
    response = api.post(_url(product.id), json={"global_category_id": str(inactive.id)})
    assert response.json()["code"] == "PRODUCT_CATALOG.REFERENCE_INACTIVE"


def test_inactive_product_blocks_dependents(api, session_factory) -> None:
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, status="INACTIVE")
    category = factories.category(session_factory, "ARROZ")

    response = api.post(_url(product.id), json={"global_category_id": str(category.id)})

    assert response.json()["code"] == "PRODUCT_CATALOG.PRODUCT_INACTIVE"


def test_deactivate_requires_deactivate_permission(api, api_as, session_factory) -> None:
    product, _, arroz = _setup(session_factory)
    only = api.post(_url(product.id), json={"global_category_id": str(arroz.id)}).json()

    response = api_as("products:update").post(f"{_url(product.id)}/{only['id']}/deactivate", json={"version": 1})

    assert response.status_code == 403
