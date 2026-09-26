"""Historia 9: activos digitales (FR-067 a FR-069)."""

from tests import factories


def _url(product_id) -> str:
    return f"/api/v1/products/{product_id}/assets"


def _image(**overrides) -> dict:
    return {
        "asset_type": "IMAGE",
        "file_name": "frente.png",
        "storage_uri": "s3://sio-assets/productos/frente.png",
        "mime_type": "image/png",
        **overrides,
    }


def _product(session_factory):
    unit = factories.unit(session_factory)
    return factories.product(session_factory, unit.id)


def test_register_asset(api, session_factory) -> None:
    product = _product(session_factory)

    response = api.post(_url(product.id), json=_image(is_primary=True))

    assert response.status_code == 201
    assert response.json()["is_primary"] is True


def test_primary_switch_per_type(api, session_factory) -> None:
    product = _product(session_factory)
    first = api.post(_url(product.id), json=_image(is_primary=True)).json()
    second = api.post(_url(product.id), json=_image(file_name="lado.png")).json()
    manual = api.post(
        _url(product.id),
        json=_image(asset_type="MANUAL", file_name="manual.pdf", mime_type="application/pdf", is_primary=True),
    ).json()

    api.post(f"{_url(product.id)}/{second['id']}/set-primary", json={"version": 1})

    primaries = {item["id"]: item["is_primary"] for item in api.get(_url(product.id)).json()}
    assert primaries == {first["id"]: False, second["id"]: True, manual["id"]: True}


def test_invalid_uri_and_mime(api, session_factory) -> None:
    product = _product(session_factory)

    relative = api.post(_url(product.id), json=_image(storage_uri="productos/frente.png"))
    no_host = api.post(_url(product.id), json=_image(storage_uri="https:///frente.png"))
    bad_mime = api.post(_url(product.id), json=_image(mime_type="png"))

    assert relative.json()["code"] == "PRODUCT_CATALOG.INVALID_STORAGE_URI"
    assert no_host.json()["code"] == "PRODUCT_CATALOG.INVALID_STORAGE_URI"
    assert bad_mime.status_code == 422


def test_binary_content_not_accepted(api, session_factory) -> None:
    product = _product(session_factory)
    response = api.post(_url(product.id), json=_image(content="iVBORw0KGgo="))
    assert response.status_code == 422


def test_deactivate_hides_from_detail_and_keeps_record(api, api_as, session_factory) -> None:
    product = _product(session_factory)
    asset = api.post(_url(product.id), json=_image()).json()

    assert api_as("products:update").post(
        f"{_url(product.id)}/{asset['id']}/deactivate", json={"version": 1}
    ).status_code == 403
    assert api.post(f"{_url(product.id)}/{asset['id']}/deactivate", json={"version": 1}).status_code == 200

    detail = api.get(f"/api/v1/products/{product.id}?expand=detail").json()["detail"]
    assert detail["assets"] == []
    assert api.get(f"{_url(product.id)}?status=INACTIVE").json()[0]["id"] == asset["id"]


def test_update_metadata(api, session_factory) -> None:
    product = _product(session_factory)
    asset = api.post(_url(product.id), json=_image()).json()

    response = api.put(
        f"{_url(product.id)}/{asset['id']}",
        json={"file_name": "frente-v2.png", "storage_uri": "s3://sio-assets/v2.png", "mime_type": None, "version": 1},
    )

    assert response.status_code == 200
    assert response.json()["file_name"] == "frente-v2.png"
    assert response.json()["mime_type"] is None
