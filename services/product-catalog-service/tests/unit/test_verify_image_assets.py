"""Verificación de solo lectura de las imágenes registradas (spec 022, FR-022-99; T054)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from product_catalog_service.tools.verify_image_assets import (
    CONTENT_MISMATCH,
    EMPTY_OBJECT,
    NOT_ELIGIBLE,
    OBJECT_MISSING,
    OK,
    SHA_MISMATCH,
    STORAGE_UNAVAILABLE,
    main,
    verify,
)
from tests.api.test_asset_content_api import FakeAssetStorage

BUCKET = "sio-product-assets"
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 40


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Asset:
    storage_uri: str
    mime_type: str | None = "image/png"
    asset_type: str = "IMAGE"
    status: str = "ACTIVE"
    is_primary: bool = True
    id: UUID = field(default_factory=uuid4)
    global_product_id: UUID = field(default_factory=uuid4)


def _uri(data: bytes) -> str:
    return f"s3://{BUCKET}/assets/{_sha(data)}.png"


def test_report_classifies_every_case_without_internal_keys() -> None:
    storage = FakeAssetStorage()
    html = b"<html>no es imagen</html>"
    wrong = b"\x89PNG\r\n\x1a\notro"
    storage.put(f"assets/{_sha(PNG)}.png", PNG, content_type="image/png", metadata={"sha256": _sha(PNG)})
    storage.put(f"assets/{_sha(html)}.png", html, content_type="image/png")
    storage.put(f"assets/{_sha(wrong)}.png", wrong, content_type="image/png", metadata={"sha256": "0" * 64})
    empty = b""
    storage.put(f"assets/{_sha(b'vacio')}.png", empty, content_type="image/png")
    assets = [
        Asset(_uri(PNG)),
        Asset(_uri(b"no subido")),
        Asset(_uri(html)),
        Asset(_uri(wrong)),
        Asset(f"s3://{BUCKET}/assets/{_sha(b'vacio')}.png"),
        Asset(_uri(PNG), mime_type="image/svg+xml"),
        Asset("https://cdn.example.com/a.png"),
    ]

    report = verify(assets, storage, BUCKET)

    assert [item["result"] for item in report["assets"]] == [
        OK, OBJECT_MISSING, CONTENT_MISMATCH, SHA_MISMATCH, EMPTY_OBJECT, NOT_ELIGIBLE, NOT_ELIGIBLE,
    ]
    assert report["totals"][OK] == 1 and report["totals"][NOT_ELIGIBLE] == 2
    text = json.dumps(report)
    for internal in (BUCKET, "assets/", "s3://", "cdn.example.com"):
        assert internal not in text


def test_storage_down_is_reported_not_raised() -> None:
    storage = FakeAssetStorage()
    storage.unavailable = True
    assert verify([Asset(_uri(PNG))], storage, BUCKET)["assets"][0]["result"] == STORAGE_UNAVAILABLE


def test_only_reads_the_storage() -> None:
    storage = FakeAssetStorage()
    storage.put(f"assets/{_sha(PNG)}.png", PNG, content_type="image/png")
    before = dict(storage.objects)
    verify([Asset(_uri(PNG))], storage, BUCKET)
    assert storage.objects == before
    assert set(storage.calls) <= {"get", "head"}


def test_cli_requires_explicit_confirmation(capsys) -> None:
    assert main([]) == 2
    assert "autorización" in capsys.readouterr().err
