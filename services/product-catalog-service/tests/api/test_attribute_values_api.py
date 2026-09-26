"""Historia 6: valores de atributo (FR-044 a FR-048, DS-08, RC-05, RC-10)."""

from tests import factories


def _url(product_id, definition_id=None) -> str:
    base = f"/api/v1/products/{product_id}/attribute-values"
    return f"{base}/{definition_id}" if definition_id else base


def _setup(session_factory):
    unit = factories.unit(session_factory)
    leches = factories.category(session_factory, "LECHES")
    tallas = factories.category(session_factory, "TALLAS")
    fat = factories.definition(session_factory, "PORCENTAJE_GRASA", "DECIMAL")
    color = factories.definition(session_factory, "COLOR", "OPTION")
    size = factories.definition(session_factory, "TALLA", "OPTION")
    red = factories.option(session_factory, color.id, "RED")
    large = factories.option(session_factory, size.id, "L")
    factories.category_attribute(session_factory, leches.id, fat.id)
    factories.category_attribute(session_factory, leches.id, color.id, required=False)
    factories.category_attribute(session_factory, tallas.id, size.id, required=False)
    product = factories.product(session_factory, unit.id, "Leche")
    association = factories.product_category(session_factory, product.id, leches.id)
    return product, fat, color, size, red, large, association


def test_register_and_replace_decimal(api, session_factory) -> None:
    product, fat, *_ = _setup(session_factory)

    created = api.put(_url(product.id, fat.id), json={"decimal_value": 3.5})
    assert created.status_code == 201
    assert created.json()["decimal_value"] == "3.50000000"

    stale = api.put(_url(product.id, fat.id), json={"decimal_value": 2, "version": 5})
    assert stale.json()["code"] == "PRODUCT_CATALOG.VERSION_CONFLICT"

    missing_version = api.put(_url(product.id, fat.id), json={"decimal_value": 2})
    assert missing_version.status_code == 422

    replaced = api.put(_url(product.id, fat.id), json={"decimal_value": 2, "version": 1})
    assert replaced.status_code == 200
    assert replaced.json()["version"] == 2


def test_type_mismatch(api, session_factory) -> None:
    product, fat, *_ = _setup(session_factory)

    wrong_field = api.put(_url(product.id, fat.id), json={"text_value": "alto"})
    two_values = api.put(_url(product.id, fat.id), json={"decimal_value": 1, "integer_value": 1})
    not_a_number = api.put(_url(product.id, fat.id), json={"decimal_value": "alto"})

    assert wrong_field.json()["code"] == "PRODUCT_CATALOG.VALUE_TYPE_MISMATCH"
    assert two_values.json()["code"] == "PRODUCT_CATALOG.VALUE_TYPE_MISMATCH"
    assert not_a_number.status_code == 422


def test_option_must_belong_to_definition(api, session_factory) -> None:
    product, _, color, _, red, large, _ = _setup(session_factory)

    wrong = api.put(_url(product.id, color.id), json={"option_id": str(large.id)})
    ok = api.put(_url(product.id, color.id), json={"option_id": str(red.id)})

    assert wrong.json()["code"] == "PRODUCT_CATALOG.OPTION_NOT_IN_DEFINITION"
    assert ok.status_code == 201


def test_inactive_option_rejected(api, session_factory) -> None:
    product, _, color, *_ = _setup(session_factory)
    old = factories.option(session_factory, color.id, "OLD", status="INACTIVE")

    response = api.put(_url(product.id, color.id), json={"option_id": str(old.id)})

    assert response.json()["code"] == "PRODUCT_CATALOG.OPTION_NOT_IN_DEFINITION"


def test_not_applicable_attribute(api, session_factory) -> None:
    product, _, _, size, _, large, _ = _setup(session_factory)

    response = api.put(_url(product.id, size.id), json={"option_id": str(large.id)})

    assert response.json()["code"] == "PRODUCT_CATALOG.ATTRIBUTE_NOT_APPLICABLE"


def test_out_of_classification_value_kept_and_locked(api, session_factory) -> None:
    product, fat, _, _, _, _, association = _setup(session_factory)
    value = api.put(_url(product.id, fat.id), json={"decimal_value": 3.5}).json()

    api.post(f"/api/v1/products/{product.id}/categories/{association.id}/deactivate", json={"version": 1})

    listed = api.get(_url(product.id)).json()
    assert listed[0]["id"] == value["id"]
    assert listed[0]["out_of_classification"] is True

    locked = api.put(_url(product.id, fat.id), json={"decimal_value": 1, "version": 1})
    assert locked.json()["code"] == "PRODUCT_CATALOG.VALUE_OUT_OF_CLASSIFICATION"


def test_delete_removes_value(api, api_as, session_factory) -> None:
    product, fat, *_ = _setup(session_factory)
    api.put(_url(product.id, fat.id), json={"decimal_value": 3.5})

    assert api_as("products:update").delete(f"{_url(product.id, fat.id)}?version=1").status_code == 403
    assert api.delete(f"{_url(product.id, fat.id)}?version=9").json()["code"] == "PRODUCT_CATALOG.VERSION_CONFLICT"
    assert api.delete(f"{_url(product.id, fat.id)}?version=1").status_code == 204
    assert api.get(_url(product.id)).json() == []


def test_inactive_product_rejects_values(api, session_factory) -> None:
    product, fat, *_ = _setup(session_factory)
    api.post(f"/api/v1/products/{product.id}/deactivate", json={"version": 1})

    response = api.put(_url(product.id, fat.id), json={"decimal_value": 3.5})

    assert response.json()["code"] == "PRODUCT_CATALOG.PRODUCT_INACTIVE"


def test_values_satisfy_completeness(api, session_factory) -> None:
    product, fat, *_ = _setup(session_factory)
    factories.presentation(session_factory, product.id)
    assert api.get(f"/api/v1/products/{product.id}").json()["eligible_for_adoption"] is False

    api.put(_url(product.id, fat.id), json={"decimal_value": 3.5})

    assert api.get(f"/api/v1/products/{product.id}").json()["eligible_for_adoption"] is True
