"""Imágenes por presentación: carga, gestión, duplicados y contenido (spec 024, historias 1 a 3 y 6).

El almacenamiento de objetos es un doble en memoria (`FakeAssetStorage`); la base es la de pruebas.
"""

from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from product_catalog_service.main import create_app
from tests import factories, images
from tests.api.test_asset_content_api import FakeAssetStorage
from tests.conftest import ApiClient
from tests.spec022_support import BUCKET, PUBLIC_BASE, spec022_settings

V = "/api/v1"
ADMIN = "perm:product-catalog:all:all"


@pytest.fixture
def storage() -> FakeAssetStorage:
    return FakeAssetStorage()


@pytest.fixture
def limits() -> dict:
    return {}


@pytest.fixture
def client(test_database_url, clean_database, test_auth, fake_manufacturer_directory, storage, limits):
    settings = spec022_settings(test_database_url, **limits)
    app = create_app(settings, auth=test_auth, manufacturer_directory_factory=lambda r: fake_manufacturer_directory,
                     asset_storage=storage)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin(client, make_token) -> ApiClient:
    return ApiClient(client, make_token(ADMIN))


@pytest.fixture
def as_user(client, make_token):
    def _build(*permissions: str) -> ApiClient:
        return ApiClient(client, make_token(*[f"perm:product-catalog:{p}" for p in permissions]) if permissions else None)
    return _build


@pytest.fixture
def catalog(session_factory):
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, "Gaseosa cola")
    bottle = factories.presentation(session_factory, product.id, "BOTELLA600")
    can = factories.presentation(session_factory, product.id, "LATA330")
    return product, bottle, can


def base(product_id, presentation_id) -> str:
    return f"{V}/products/{product_id}/presentations/{presentation_id}/assets"


def upload(client: ApiClient, product_id, presentation_id, content: bytes, name: str = "frente.png", **kwargs):
    return client.post(f"{base(product_id, presentation_id)}/upload",
                       files={"file": (name, content, kwargs.pop("declared", "application/octet-stream"))}, **kwargs)


def row(session_factory, asset_id):
    with session_factory() as session:
        return session.execute(text("SELECT * FROM product_assets WHERE id = :id"), {"id": asset_id}).mappings().one()


def count_assets(session_factory) -> int:
    with session_factory() as session:
        return session.execute(text("SELECT count(*) FROM product_assets")).scalar_one()


# ----------------------------------------------------------------- historia 1: carga


def test_upload_creates_primary_image_and_serves_same_bytes(admin, catalog, storage, session_factory) -> None:
    product, bottle, _ = catalog
    content = images.png()
    sha = hashlib.sha256(content).hexdigest()

    response = upload(admin, product.id, bottle.id, content, "C:\\fotos\\Botella 600.png")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["asset_type"] == "IMAGE" and body["status"] == "ACTIVE" and body["is_primary"] is True
    assert body["mime_type"] == "image/png" and body["file_name"] == "Botella 600.png"
    assert body["global_product_presentation_id"] == str(bottle.id)
    assert response.headers["location"] == f"{base(product.id, bottle.id)}/{body['id']}"
    assert body["content_url"] == f"{base(product.id, bottle.id)}/{body['id']}/content"
    assert body["image_url"].startswith(f"{PUBLIC_BASE}/api/v1/public/product-images?ref=")
    for hidden in ("storage_uri", BUCKET, f"assets/{sha}"):
        assert hidden not in response.text
    assert storage.objects[f"assets/{sha}.png"][2] == {"sha256": sha}
    assert row(session_factory, body["id"])["storage_uri"] == f"s3://{BUCKET}/assets/{sha}.png"

    served = admin.get(body["content_url"])
    assert served.status_code == 200 and served.content == content
    assert served.headers["etag"] == f'"{sha}"'
    public = TestClient(admin._client.app).get(body["image_url"].removeprefix(PUBLIC_BASE))
    assert public.status_code == 200 and public.content == content


@pytest.mark.parametrize(("content", "mime"), [(images.jpeg(), "image/jpeg"), (images.webp(), "image/webp")])
def test_upload_jpeg_and_webp(admin, catalog, content, mime) -> None:
    product, bottle, _ = catalog
    response = upload(admin, product.id, bottle.id, content, "foto.png", declared="image/png")
    assert response.status_code == 201 and response.json()["mime_type"] == mime


def test_last_upload_becomes_primary_and_previous_is_kept(admin, catalog) -> None:
    product, bottle, _ = catalog
    first = upload(admin, product.id, bottle.id, images.png((1, 1, 1))).json()
    second = upload(admin, product.id, bottle.id, images.png((2, 2, 2))).json()

    listed = admin.get(base(product.id, bottle.id)).json()

    assert [item["id"] for item in listed] == [second["id"], first["id"]]
    assert [item["is_primary"] for item in listed] == [True, False]
    assert all(item["status"] == "ACTIVE" for item in listed)


@pytest.mark.parametrize(
    ("content", "status", "code"),
    [
        (b"<html><script>x</script></html>", 415, "UNSUPPORTED_MEDIA_TYPE"),
        (images.gif(), 415, "UNSUPPORTED_MEDIA_TYPE"),
        (b"%PDF-1.4 falso", 415, "UNSUPPORTED_MEDIA_TYPE"),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, 422, "INVALID_IMAGE"),
        (images.jpeg(size=(40, 40))[:120], 422, "INVALID_IMAGE"),
    ],
    ids=["html", "gif", "pdf", "png-corrupto", "jpeg-truncado"],
)
def test_invalid_files_are_rejected_without_object_or_record(admin, catalog, storage, session_factory, content,
                                                             status, code) -> None:
    product, bottle, _ = catalog
    response = upload(admin, product.id, bottle.id, content, "foto.jpg", declared="image/jpeg")
    assert response.status_code == status and response.json()["code"] == f"PRODUCT_CATALOG.{code}"
    assert storage.objects == {} and count_assets(session_factory) == 0


def test_empty_or_missing_file_is_rejected(admin, catalog, storage) -> None:
    product, bottle, _ = catalog
    empty = upload(admin, product.id, bottle.id, b"")
    missing = admin.post(f"{base(product.id, bottle.id)}/upload", files={"otro": ("a.png", images.png(), "image/png")})
    not_multipart = admin.post(f"{base(product.id, bottle.id)}/upload", json={"file": "x"})
    for response in (empty, missing, not_multipart):
        assert response.status_code == 422 and response.json()["code"] == "PRODUCT_CATALOG.VALIDATION_ERROR"
    assert storage.objects == {}


def test_extra_form_fields_are_rejected(admin, catalog, storage) -> None:
    product, bottle, _ = catalog
    response = admin.post(f"{base(product.id, bottle.id)}/upload",
                          files={"file": ("a.png", images.png(), "image/png")}, data={"is_primary": "false"})
    assert response.status_code == 422 and response.json()["errors"][0]["field"] == "is_primary"
    assert storage.objects == {}


class TestLimits:
    content = images.png(size=(10, 10))

    @pytest.fixture
    def limits(self) -> dict:
        return {"asset_upload_max_bytes": len(self.content), "asset_upload_max_pixels": 100}

    def test_exact_size_is_accepted(self, admin, catalog) -> None:
        product, bottle, _ = catalog
        assert upload(admin, product.id, bottle.id, self.content).status_code == 201

    def test_one_byte_more_is_rejected(self, admin, catalog, storage) -> None:
        product, bottle, _ = catalog
        response = upload(admin, product.id, bottle.id, self.content + b"\x00")
        assert response.status_code == 413 and response.json()["code"] == "PRODUCT_CATALOG.FILE_TOO_LARGE"
        assert storage.objects == {}

    def test_body_far_above_limit_is_cut_before_parsing(self, admin, catalog, storage) -> None:
        product, bottle, _ = catalog
        response = upload(admin, product.id, bottle.id, b"\x89PNG" + b"\x00" * (200 * 1024))
        assert response.status_code == 413 and storage.objects == {}



class TestPixelLimit:
    @pytest.fixture
    def limits(self) -> dict:
        return {"asset_upload_max_pixels": 100}

    def test_exact_pixels_are_accepted(self, admin, catalog) -> None:
        product, bottle, _ = catalog
        assert upload(admin, product.id, bottle.id, images.png(size=(10, 10))).status_code == 201

    def test_pixels_above_limit_are_rejected(self, admin, catalog, storage) -> None:
        product, bottle, _ = catalog
        response = upload(admin, product.id, bottle.id, images.png(size=(11, 10)))
        assert response.status_code == 422
        assert response.json()["code"] == "PRODUCT_CATALOG.IMAGE_DIMENSIONS_EXCEEDED"
        assert storage.objects == {}


def test_missing_product_or_presentation_returns_404(admin, catalog, storage) -> None:
    product, bottle, _ = catalog
    assert upload(admin, uuid4(), bottle.id, images.png()).status_code == 404
    assert upload(admin, product.id, uuid4(), images.png()).status_code == 404
    assert storage.objects == {}


def test_inactive_product_or_presentation_and_other_product_are_rejected(admin, catalog, session_factory,
                                                                         storage) -> None:
    product, bottle, _ = catalog
    unit = factories.unit(session_factory, "KG")
    other = factories.product(session_factory, unit.id, "Gaseosa naranja")
    foreign = factories.presentation(session_factory, other.id, "BOTELLA")
    inactive_presentation = factories.presentation(session_factory, product.id, "VIEJA", status="INACTIVE")
    inactive_product = factories.product(session_factory, unit.id, "Descontinuado", status="INACTIVE")
    its_presentation = factories.presentation(session_factory, inactive_product.id, "UNIDAD")

    cases = [
        (product.id, foreign.id, "PRESENTATION_OF_OTHER_PRODUCT"),
        (product.id, inactive_presentation.id, "PRESENTATION_INACTIVE"),
        (inactive_product.id, its_presentation.id, "PRODUCT_INACTIVE"),
    ]
    for product_id, presentation_id, code in cases:
        response = upload(admin, product_id, presentation_id, images.png())
        assert response.status_code == 422 and response.json()["code"] == f"PRODUCT_CATALOG.{code}"
    assert storage.objects == {}


def test_authentication_and_permission(as_user, catalog, storage) -> None:
    product, bottle, _ = catalog
    assert upload(as_user(), product.id, bottle.id, images.png()).status_code == 401
    assert upload(as_user("products:read"), product.id, bottle.id, images.png()).status_code == 403
    assert upload(as_user("products:deactivate"), product.id, bottle.id, images.png()).status_code == 403
    assert storage.objects == {}
    assert upload(as_user("products:update"), product.id, bottle.id, images.png()).status_code == 201


def test_storage_unavailable_returns_503_without_record(admin, catalog, storage, session_factory) -> None:
    product, bottle, _ = catalog
    storage.unavailable = True
    response = upload(admin, product.id, bottle.id, images.png())
    assert response.status_code == 503 and response.json()["dependency"] == "asset-storage"
    assert count_assets(session_factory) == 0


def test_database_failure_after_write_leaves_unreferenced_object(admin, catalog, storage, session_factory,
                                                                 monkeypatch) -> None:
    """FR-024-29: sin referencia y sin borrar el objeto; la reconciliación lo informa (caso 21)."""
    from product_catalog_service.application import presentation_image_service as module

    product, bottle, _ = catalog
    original = module.lock_product

    def broken(session, product_id):
        raise OperationalError("SELECT 1", {}, Exception("conexión perdida"), connection_invalidated=True)

    monkeypatch.setattr(module, "lock_product", broken)
    content = images.png((9, 9, 9))
    response = upload(admin, product.id, bottle.id, content)
    monkeypatch.setattr(module, "lock_product", original)

    assert response.status_code == 503 and response.json()["dependency"] == "database"
    sha = hashlib.sha256(content).hexdigest()
    assert f"assets/{sha}.png" in storage.objects  # el objeto no se borra
    assert count_assets(session_factory) == 0


def test_final_check_rejects_when_presentation_was_deactivated_meanwhile(admin, catalog, storage, session_factory,
                                                                        monkeypatch) -> None:
    product, bottle, _ = catalog
    original = storage.put_if_absent

    def deactivate_then_write(key, data, **kwargs):
        with session_factory() as session:
            session.execute(text("UPDATE global_product_presentations SET status = 'INACTIVE' WHERE id = :id"),
                            {"id": bottle.id})
            session.commit()
        return original(key, data, **kwargs)

    monkeypatch.setattr(storage, "put_if_absent", deactivate_then_write)
    response = upload(admin, product.id, bottle.id, images.png())
    assert response.status_code == 422 and response.json()["code"] == "PRODUCT_CATALOG.PRESENTATION_INACTIVE"
    assert len(storage.objects) == 1 and count_assets(session_factory) == 0


# ----------------------------------------------------------------- historia 3: duplicados


def test_duplicate_active_content_returns_409_with_existing_id(admin, catalog, storage, session_factory) -> None:
    product, bottle, _ = catalog
    first = upload(admin, product.id, bottle.id, images.png()).json()
    storage.calls.clear()

    again = upload(admin, product.id, bottle.id, images.png(), "otro-nombre.png")

    assert again.status_code == 409
    assert again.json()["code"] == "PRODUCT_CATALOG.DUPLICATE_ASSET_CONTENT"
    assert again.json()["existing_asset_id"] == first["id"]
    assert storage.calls == [] and count_assets(session_factory) == 1


def test_duplicate_inactive_content_is_reactivated_as_primary(admin, catalog, storage) -> None:
    product, bottle, _ = catalog
    old = upload(admin, product.id, bottle.id, images.png((1, 1, 1))).json()
    newer = upload(admin, product.id, bottle.id, images.png((2, 2, 2))).json()
    admin.post(f"{base(product.id, bottle.id)}/{old['id']}/deactivate", json={"version": old["version"] + 1})

    again = upload(admin, product.id, bottle.id, images.png((1, 1, 1)))

    assert again.status_code == 200, again.text
    body = again.json()
    assert body["id"] == old["id"] and body["is_primary"] is True and body["status"] == "ACTIVE"
    assert body["version"] > old["version"]
    listed = admin.get(base(product.id, bottle.id)).json()
    assert [(item["id"], item["is_primary"]) for item in listed] == [(old["id"], True), (newer["id"], False)]


def test_duplicate_inactive_with_missing_object_restores_it_first(admin, catalog, storage) -> None:
    product, bottle, _ = catalog
    content = images.png((5, 5, 5))
    first = upload(admin, product.id, bottle.id, content).json()
    admin.post(f"{base(product.id, bottle.id)}/{first['id']}/deactivate", json={"version": first["version"]})
    storage.objects.clear()

    again = upload(admin, product.id, bottle.id, content)

    assert again.status_code == 200 and again.json()["id"] == first["id"]
    assert admin.get(again.json()["content_url"]).content == content


def test_same_content_in_other_presentation_is_a_new_image_sharing_the_object(admin, catalog, storage) -> None:
    product, bottle, can = catalog
    first = upload(admin, product.id, bottle.id, images.png()).json()
    second = upload(admin, product.id, can.id, images.png())
    assert second.status_code == 201 and second.json()["id"] != first["id"]
    assert len(storage.objects) == 1


def test_object_with_different_integrity_is_never_replaced(admin, catalog, storage, session_factory) -> None:
    product, bottle, _ = catalog
    content = images.png()
    key = f"assets/{hashlib.sha256(content).hexdigest()}.png"
    storage.put(key, b"otro", content_type="image/png", metadata={"sha256": "0" * 64})
    response = upload(admin, product.id, bottle.id, content)
    assert response.status_code == 503
    assert storage.objects[key][0] == b"otro" and count_assets(session_factory) == 0


# ----------------------------------------------------------------- historia 2: gestión


def _three(admin, product, presentation):
    return [upload(admin, product.id, presentation.id, images.png((n, n, n))).json() for n in (1, 2, 3)]


def _current(admin, product, presentation, asset_id):
    for status in ("ACTIVE", "INACTIVE"):
        for item in admin.get(base(product.id, presentation.id), params={"status": status}).json():
            if item["id"] == asset_id:
                return item
    raise AssertionError(asset_id)


def test_set_primary_and_rejections(admin, catalog) -> None:
    product, bottle, can = catalog
    first, second, third = _three(admin, product, bottle)
    other = upload(admin, product.id, can.id, images.png((7, 7, 7))).json()
    url = base(product.id, bottle.id)

    current = _current(admin, product, bottle, first["id"])
    changed = admin.post(f"{url}/{first['id']}/set-primary", json={"version": current["version"]})
    assert changed.status_code == 200 and changed.json()["is_primary"] is True
    assert _current(admin, product, bottle, third["id"])["is_primary"] is False

    assert admin.post(f"{url}/{other['id']}/set-primary", json={"version": other["version"]}).status_code == 404
    stale = admin.post(f"{url}/{second['id']}/set-primary", json={"version": 999})
    assert stale.status_code == 409 and stale.json()["code"] == "PRODUCT_CATALOG.VERSION_CONFLICT"
    second_now = _current(admin, product, bottle, second["id"])
    admin.post(f"{url}/{second['id']}/deactivate", json={"version": second_now["version"]})
    inactive = _current(admin, product, bottle, second["id"])
    rejected = admin.post(f"{url}/{second['id']}/set-primary", json={"version": inactive["version"]})
    assert rejected.status_code == 422 and rejected.json()["code"] == "PRODUCT_CATALOG.REFERENCE_INACTIVE"


def test_deactivate_secondary_keeps_primary_and_object(admin, catalog, storage) -> None:
    product, bottle, _ = catalog
    first, _, third = _three(admin, product, bottle)
    current = _current(admin, product, bottle, first["id"])
    response = admin.post(f"{base(product.id, bottle.id)}/{first['id']}/deactivate", json={"version": current["version"]})
    assert response.status_code == 200 and response.json()["status"] == "INACTIVE"
    assert response.json()["image_url"] is None
    assert _current(admin, product, bottle, third["id"])["is_primary"] is True
    assert len(storage.objects) == 3
    assert first["id"] not in [item["id"] for item in admin.get(base(product.id, bottle.id)).json()]


def test_deactivate_primary_promotes_latest_with_id_tiebreak(admin, catalog, session_factory) -> None:
    product, bottle, _ = catalog
    first, second, third = _three(admin, product, bottle)
    with session_factory() as session:  # empate en created_at entre las dos restantes
        session.execute(text("UPDATE product_assets SET created_at = '2026-01-01T00:00:00Z' WHERE id IN (:a, :b)"),
                        {"a": first["id"], "b": second["id"]})
        session.commit()
    expected = max(first["id"], second["id"])

    current = _current(admin, product, bottle, third["id"])
    admin.post(f"{base(product.id, bottle.id)}/{third['id']}/deactivate", json={"version": current["version"]})

    listed = admin.get(base(product.id, bottle.id)).json()
    assert listed[0]["id"] == expected and listed[0]["is_primary"] is True
    assert sum(item["is_primary"] for item in listed) == 1


def test_deactivate_last_image_leaves_presentation_without_primary(admin, catalog) -> None:
    product, bottle, _ = catalog
    only = upload(admin, product.id, bottle.id, images.png()).json()
    admin.post(f"{base(product.id, bottle.id)}/{only['id']}/deactivate", json={"version": only["version"]})
    assert admin.get(base(product.id, bottle.id)).json() == []


def test_reactivate_does_not_change_primary(admin, catalog) -> None:
    product, bottle, _ = catalog
    only = upload(admin, product.id, bottle.id, images.png()).json()
    url = f"{base(product.id, bottle.id)}/{only['id']}"
    deactivated = admin.post(f"{url}/deactivate", json={"version": only["version"]}).json()

    reactivated = admin.post(f"{url}/reactivate", json={"version": deactivated["version"]})

    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "ACTIVE" and reactivated.json()["is_primary"] is False
    assert [item["is_primary"] for item in admin.get(base(product.id, bottle.id)).json()] == [False]


def test_list_active_inactive_and_order(admin, catalog) -> None:
    product, bottle, _ = catalog
    first, second, third = _three(admin, product, bottle)
    current = _current(admin, product, bottle, second["id"])
    admin.post(f"{base(product.id, bottle.id)}/{second['id']}/deactivate", json={"version": current["version"]})

    active = admin.get(base(product.id, bottle.id)).json()
    inactive = admin.get(base(product.id, bottle.id), params={"status": "INACTIVE"}).json()

    assert [item["id"] for item in active] == [third["id"], first["id"]]
    assert [item["id"] for item in inactive] == [second["id"]]
    assert admin.get(base(product.id, uuid4())).status_code == 404


def test_rename_only_changes_file_name(admin, catalog) -> None:
    product, bottle, _ = catalog
    image = upload(admin, product.id, bottle.id, images.png()).json()
    url = f"{base(product.id, bottle.id)}/{image['id']}"

    renamed = admin.put(url, json={"file_name": "../frente\x01 nueva.png", "version": image["version"]})
    assert renamed.status_code == 200 and renamed.json()["file_name"] == "frente nueva.png"

    for field, value in [("storage_uri", "s3://x/y"), ("mime_type", "image/png"), ("is_primary", False),
                         ("global_product_presentation_id", str(uuid4())), ("status", "INACTIVE"),
                         ("asset_type", "IMAGE")]:
        rejected = admin.put(url, json={"file_name": "x.png", "version": renamed.json()["version"], field: value})
        assert rejected.status_code == 422 and rejected.json()["code"] == "PRODUCT_CATALOG.IMMUTABLE_FIELD", field


def test_content_by_presentation_route(admin, as_user, catalog) -> None:
    product, bottle, can = catalog
    content = images.png()
    image = upload(admin, product.id, bottle.id, content).json()
    reader = as_user("products:read")

    ok = reader.get(image["content_url"])
    assert ok.status_code == 200 and ok.content == content
    not_modified = reader.get(image["content_url"], headers={"If-None-Match": ok.headers["etag"]})
    assert not_modified.status_code == 304
    assert reader.get(f"{base(product.id, can.id)}/{image['id']}/content").status_code == 404
    assert as_user().get(image["content_url"]).status_code == 401


def test_management_permissions(as_user, admin, catalog) -> None:
    product, bottle, _ = catalog
    image = upload(admin, product.id, bottle.id, images.png()).json()
    url = f"{base(product.id, bottle.id)}/{image['id']}"
    updater = as_user("products:update")
    assert updater.post(f"{url}/deactivate", json={"version": image["version"]}).status_code == 403
    assert as_user("products:read").post(f"{url}/set-primary", json={"version": image["version"]}).status_code == 403
    assert as_user("products:deactivate").post(f"{url}/deactivate", json={"version": image["version"]}).status_code == 200


# ----------------------------------------------------------------- registro por referencia (historia 6)


def _stored(storage, content: bytes, ext: str = "png", sha: str | None = None) -> str:
    digest = hashlib.sha256(content).hexdigest()
    key = f"assets/{digest}.{ext}"
    storage.put(key, content, content_type="image/png", metadata={"sha256": sha or digest})
    return f"s3://{BUCKET}/{key}"


def test_reference_registration_accepts_stored_image(admin, catalog, storage) -> None:
    product, bottle, _ = catalog
    uri = _stored(storage, images.png())
    response = admin.post(base(product.id, bottle.id), json={"file_name": "BOX-3__frente.png", "storage_uri": uri,
                                                             "mime_type": "image/png", "is_primary": True})
    assert response.status_code == 201, response.text
    assert response.json()["is_primary"] is True and "storage_uri" not in response.json()


@pytest.mark.parametrize(
    ("case", "field"),
    [("externa", "storage_uri"), ("sin-sha", "storage_uri"), ("tipo", "mime_type"), ("extension", "storage_uri"),
     ("inexistente", "storage_uri"), ("metadata", "storage_uri")],
)
def test_reference_registration_rejections(admin, catalog, storage, session_factory, case, field) -> None:
    product, bottle, _ = catalog
    content = images.png()
    digest = hashlib.sha256(content).hexdigest()
    body = {"file_name": "a.png", "mime_type": "image/png", "is_primary": False}
    if case == "externa":
        body["storage_uri"] = f"https://cdn.example.com/assets/{digest}.png"
    elif case == "sin-sha":
        body["storage_uri"] = f"s3://{BUCKET}/assets/frente.png"
    elif case == "tipo":
        body.update(storage_uri=_stored(storage, content), mime_type="image/gif")
    elif case == "extension":
        body.update(storage_uri=_stored(storage, content), mime_type="image/jpeg")
    elif case == "inexistente":
        body["storage_uri"] = f"s3://{BUCKET}/assets/{digest}.png"
    else:
        body["storage_uri"] = _stored(storage, content, sha="f" * 64)
    response = admin.post(base(product.id, bottle.id), json=body)
    assert response.status_code == 422, response.text
    errors = response.json().get("errors") or [{}]
    assert errors[0].get("field") in {field, f"body.{field}", None} or field in response.text
    assert count_assets(session_factory) == 0


def test_reference_duplicate_inactive_returns_409(admin, catalog, storage) -> None:
    product, bottle, _ = catalog
    uri = _stored(storage, images.png())
    body = {"file_name": "a.png", "storage_uri": uri, "mime_type": "image/png", "is_primary": True}
    created = admin.post(base(product.id, bottle.id), json=body).json()
    admin.post(f"{base(product.id, bottle.id)}/{created['id']}/deactivate", json={"version": created["version"]})
    again = admin.post(base(product.id, bottle.id), json=body)
    assert again.status_code == 409 and again.json()["existing_asset_id"] == created["id"]


# ----------------------------------------------------------------- auditoría (FR-024-27)


def test_audit_events_include_hash_and_size(admin, catalog, outbox, clear_outbox) -> None:
    product, bottle, _ = catalog
    clear_outbox()
    content = images.png((1, 1, 1))
    first = upload(admin, product.id, bottle.id, content).json()
    second = upload(admin, product.id, bottle.id, images.png((2, 2, 2))).json()
    current = _current(admin, product, bottle, second["id"])
    admin.post(f"{base(product.id, bottle.id)}/{second['id']}/deactivate", json={"version": current["version"]})

    events = outbox()
    actions = [event["action"] for event in events]
    assert actions == ["CREATE_PRODUCT_ASSET", "CREATE_PRODUCT_ASSET", "SET_PRIMARY_PRODUCT_ASSET",
                       "DEACTIVATE_PRODUCT_ASSET", "SET_PRIMARY_PRODUCT_ASSET"]
    assert events[0]["new_values"]["sha256"] == hashlib.sha256(content).hexdigest()
    assert events[0]["new_values"]["size_bytes"] == len(content)
    assert events[2]["previous_values"]["previous_primary_id"] == first["id"]
    assert events[4]["entity_id"] == first["id"]
    assert events[4]["previous_values"]["previous_primary_id"] == second["id"]
