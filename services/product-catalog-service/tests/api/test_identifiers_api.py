"""Historia 7: identificadores (RC-07, FR-055 a FR-060, DS-05, DS-17)."""

from tests import factories


def _url(product_id) -> str:
    return f"/api/v1/products/{product_id}/identifiers"


def _two_products(session_factory):
    unit = factories.unit(session_factory)
    return factories.product(session_factory, unit.id, "Uno"), factories.product(session_factory, unit.id, "Dos")


def test_register_gtin_keeps_leading_zeros(api, session_factory) -> None:
    product, _ = _two_products(session_factory)

    response = api.post(_url(product.id), json={"identifier_type": "UPC", "value": "0360-0029 1452"})

    assert response.status_code == 201
    assert response.json()["value"] == "036000291452"
    assert response.json()["canonical_value"] == "00036000291452"


def test_collision_across_family_types(api, session_factory) -> None:
    first, second = _two_products(session_factory)
    existing = api.post(_url(first.id), json={"identifier_type": "UPC", "value": "036000291452"}).json()

    for identifier_type, value in (("EAN", "0036000291452"), ("GTIN", "00036000291452")):
        response = api.post(_url(second.id), json={"identifier_type": identifier_type, "value": value})
        assert response.status_code == 409
        body = response.json()
        assert body["code"] == "PRODUCT_CATALOG.IDENTIFIER_COLLISION"
        assert body["conflict"]["global_product_id"] == str(first.id)
        assert body["conflict"]["identifier_id"] == existing["id"]

    assert api.get(_url(first.id)).json()[0]["status"] == "ACTIVE"


def test_inactive_identifier_is_not_reused(api, session_factory) -> None:
    first, second = _two_products(session_factory)
    existing = api.post(_url(first.id), json={"identifier_type": "EAN", "value": "4006381333931"}).json()
    api.post(f"{_url(first.id)}/{existing['id']}/deactivate", json={"version": 1})

    response = api.post(_url(second.id), json={"identifier_type": "EAN", "value": "4006381333931"})

    assert response.status_code == 409


def test_same_code_on_product_and_its_presentation_rejected(api, session_factory) -> None:
    product, _ = _two_products(session_factory)
    box = factories.presentation(session_factory, product.id, "CAJA")
    api.post(_url(product.id), json={"identifier_type": "EAN", "value": "4006381333931"})

    response = api.post(
        _url(product.id),
        json={"identifier_type": "GTIN", "value": "04006381333931", "global_product_presentation_id": str(box.id)},
    )

    assert response.status_code == 409


def test_format_and_check_digit(api, session_factory) -> None:
    product, _ = _two_products(session_factory)

    bad_digit = api.post(_url(product.id), json={"identifier_type": "EAN", "value": "4006381333932"})
    bad_shape = api.post(_url(product.id), json={"identifier_type": "GTIN", "value": "ABC123"})

    assert bad_digit.json()["code"] == "PRODUCT_CATALOG.INVALID_CHECK_DIGIT"
    assert bad_shape.json()["code"] == "PRODUCT_CATALOG.INVALID_GTIN_FORMAT"


def test_barcode_rules(api, session_factory) -> None:
    first, second = _two_products(session_factory)

    gtin_like = api.post(_url(first.id), json={"identifier_type": "BARCODE", "value": "7702004003508"})
    assert gtin_like.json()["code"] == "PRODUCT_CATALOG.BARCODE_IS_GTIN"

    generic = api.post(_url(first.id), json={"identifier_type": "BARCODE", "value": "INT-000123"})
    assert generic.status_code == 201
    duplicate = api.post(_url(second.id), json={"identifier_type": "BARCODE", "value": "INT000123"})
    assert duplicate.status_code == 409


def test_presentation_must_belong_to_product(api, session_factory) -> None:
    first, second = _two_products(session_factory)
    foreign = factories.presentation(session_factory, second.id, "CAJA")

    response = api.post(
        _url(first.id),
        json={"identifier_type": "EAN", "value": "96385074", "global_product_presentation_id": str(foreign.id)},
    )

    assert response.json()["code"] == "PRODUCT_CATALOG.PRESENTATION_OF_OTHER_PRODUCT"


def test_primary_per_type_and_context(api, session_factory) -> None:
    product, _ = _two_products(session_factory)
    box = factories.presentation(session_factory, product.id, "CAJA")
    first = api.post(_url(product.id), json={"identifier_type": "EAN", "value": "96385074", "is_primary": True}).json()
    second = api.post(_url(product.id), json={"identifier_type": "EAN", "value": "4006381333931"}).json()
    on_box = api.post(
        _url(product.id),
        json={
            "identifier_type": "EAN",
            "value": "7702004003508",
            "global_product_presentation_id": str(box.id),
            "is_primary": True,
        },
    ).json()

    switched = api.post(f"{_url(product.id)}/{second['id']}/set-primary", json={"version": 1})

    assert switched.json()["is_primary"] is True
    items = {item["id"]: item["is_primary"] for item in api.get(_url(product.id)).json()}
    assert items == {first["id"]: False, second["id"]: True, on_box["id"]: True}


def test_no_put_for_identifiers(api, session_factory) -> None:
    product, _ = _two_products(session_factory)
    created = api.post(_url(product.id), json={"identifier_type": "EAN", "value": "96385074"}).json()

    response = api.put(f"{_url(product.id)}/{created['id']}", json={"value": "4006381333931", "version": 1})

    assert response.status_code in {404, 405}


def test_deactivate_requires_deactivate_permission(api, api_as, session_factory) -> None:
    product, _ = _two_products(session_factory)
    created = api.post(_url(product.id), json={"identifier_type": "EAN", "value": "96385074"}).json()

    response = api_as("products:update").post(f"{_url(product.id)}/{created['id']}/deactivate", json={"version": 1})

    assert response.status_code == 403
