"""Historia 7: presentaciones (RC-06, RC-09, FR-049 a FR-054, FR-050a, FR-006)."""

from tests import factories


def _create(api, product_id, **fields):
    body = {"code": "CAJA_X_20", "name": "Caja x 20", "base_quantity": 20, **fields}
    return api.post(f"/api/v1/products/{product_id}/presentations", json=body)


def _put(api, presentation: dict, **changes):
    body = {
        "name": presentation["name"],
        "display_order": presentation["display_order"],
        "packaging_type_id": presentation["packaging_type_id"],
        "base_quantity": presentation["base_quantity"],
        "content_quantity": presentation["content_quantity"],
        "content_unit_id": presentation["content_unit_id"],
        "is_base": presentation["is_base"],
        "version": presentation["version"],
        **changes,
    }
    return api.put(f"/api/v1/presentations/{presentation['id']}", json=body)


def _product(session_factory):
    unit = factories.unit(session_factory)
    return factories.product(session_factory, unit.id)


def test_create_with_packaging_and_content(api, session_factory) -> None:
    product = _product(session_factory)
    box = factories.packaging(session_factory, "BOX")
    ml = factories.unit(session_factory, "ML")

    response = _create(
        api,
        product.id,
        packaging_type_id=str(box.id),
        content_quantity=120,
        content_unit_id=str(ml.id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "CAJA_X_20"
    assert body["base_quantity"] == "20.00000000"
    assert body["content_quantity"] == "120.0000"


def test_single_base_with_factor_one(api, session_factory) -> None:
    product = _product(session_factory)

    assert _create(api, product.id, code="UNIDAD", base_quantity=1, is_base=True).status_code == 201
    second = _create(api, product.id, code="OTRA", base_quantity=1, is_base=True)
    wrong = _create(api, product.id, code="CAJA", base_quantity=20, is_base=True)

    assert second.json()["code"] == "PRODUCT_CATALOG.BASE_PRESENTATION_EXISTS"
    assert wrong.json()["code"] == "PRODUCT_CATALOG.BASE_QUANTITY_MUST_BE_ONE"


def test_content_requires_unit(api, session_factory) -> None:
    product = _product(session_factory)
    response = _create(api, product.id, content_quantity=120)
    assert response.status_code == 422


def test_duplicate_code_and_inactive_packaging(api, session_factory) -> None:
    product = _product(session_factory)
    old = factories.packaging(session_factory, "OLD", status="INACTIVE")
    _create(api, product.id)

    assert _create(api, product.id, code="caja_x_20").json()["code"] == "PRODUCT_CATALOG.DUPLICATE_CODE"
    inactive = _create(api, product.id, code="OTRA", packaging_type_id=str(old.id))
    assert inactive.json()["code"] == "PRODUCT_CATALOG.REFERENCE_INACTIVE"


def test_material_fields_editable_without_first_use(api, session_factory) -> None:
    product = _product(session_factory)
    presentation = _create(api, product.id).json()

    response = _put(api, presentation, base_quantity=24)

    assert response.status_code == 200
    assert response.json()["base_quantity"] == "24.00000000"


def test_material_fields_locked_with_first_use(api, session_factory) -> None:
    product = _product(session_factory)
    box = factories.packaging(session_factory, "BOX")
    ml = factories.unit(session_factory, "ML")
    used = factories.presentation(session_factory, product.id, "CAJA", first_used=True)
    current = api.get(f"/api/v1/presentations/{used.id}").json()

    for field, value in (
        ("packaging_type_id", str(box.id)),
        ("base_quantity", 20),
    ):
        response = _put(api, current, **{field: value})
        assert response.json()["code"] == "PRODUCT_CATALOG.PRESENTATION_LOCKED_BY_FIRST_USE"

    content = _put(api, current, content_quantity=5, content_unit_id=str(ml.id))
    assert content.json()["code"] == "PRODUCT_CATALOG.PRESENTATION_LOCKED_BY_FIRST_USE"

    renamed = _put(api, current, name="Caja grande", display_order=3)
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Caja grande"


def test_is_base_changeable_after_first_use(api, session_factory) -> None:
    product = _product(session_factory)
    used = factories.presentation(session_factory, product.id, "UNIDAD", first_used=True)
    current = api.get(f"/api/v1/presentations/{used.id}").json()

    response = _put(api, current, is_base=True)

    assert response.status_code == 200
    assert response.json()["is_base"] is True


def test_deactivating_last_presentation_makes_product_incomplete(api, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)
    presentation = api.get(f"/api/v1/products/{product.id}/presentations").json()[0]

    response = api.post(f"/api/v1/presentations/{presentation['id']}/deactivate", json={"version": 1})

    assert response.status_code == 200
    issues = api.get(f"/api/v1/products/{product.id}/completeness").json()["issues"]
    assert issues == ["NO_ACTIVE_PRESENTATION"]


def test_reactivated_base_is_not_base_again(api, session_factory) -> None:
    product = _product(session_factory)
    base = _create(api, product.id, code="UNIDAD", base_quantity=1, is_base=True).json()

    api.post(f"/api/v1/presentations/{base['id']}/deactivate", json={"version": 1})
    reactivated = api.post(f"/api/v1/presentations/{base['id']}/reactivate", json={"version": 2}).json()

    assert reactivated["status"] == "ACTIVE"
    assert reactivated["is_base"] is False


def test_deactivate_requires_deactivate_permission(api, api_as, session_factory) -> None:
    product = _product(session_factory)
    presentation = _create(api, product.id).json()

    response = api_as("products:update").post(
        f"/api/v1/presentations/{presentation['id']}/deactivate", json={"version": 1}
    )

    assert response.status_code == 403


def test_code_is_immutable(api, session_factory) -> None:
    product = _product(session_factory)
    presentation = _create(api, product.id).json()

    response = _put(api, presentation, code="OTRA")

    assert response.json()["code"] == "PRODUCT_CATALOG.IMMUTABLE_FIELD"
