"""Plan del relleno de imágenes por presentación (spec 024, casos 26, 27, 28, 34, 34b y 34c; funciones puras).

Las pruebas contra PostgreSQL (aplicación, idempotencia y simulación sin escrituras, casos 26, 27, 33 y 34) están
en `tests/contract/test_migrate_presentation_images_db.py`.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from product_catalog_service.tools import migrate_presentation_images as tool
from tests.storage_fakes import BUCKET, FakeAssetStorage


@dataclass
class Asset:
    id: UUID
    global_product_id: UUID
    global_product_presentation_id: UUID | None
    storage_uri: str
    is_primary: bool = True
    status: str = "ACTIVE"
    mime_type: str = "image/png"
    asset_type: str = "IMAGE"


def _stored(storage: FakeAssetStorage, label: str, *, metadata_sha: str | None = None) -> str:
    sha = hashlib.sha256(label.encode()).hexdigest()
    key = f"assets/{sha}.png"
    storage.put(key, label.encode(), content_type="image/png", metadata={"sha256": metadata_sha or sha})
    return f"s3://{BUCKET}/{key}"


def _image(storage, product, **kwargs) -> Asset:
    return Asset(id=uuid4(), global_product_id=product, global_product_presentation_id=None,
                 storage_uri=kwargs.pop("storage_uri", None) or _stored(storage, uuid4().hex), **kwargs)


def _mapping(pairs: dict[UUID, UUID], **kwargs) -> tool.Mapping:
    return tool.Mapping(dict(pairs), **kwargs)


@pytest.fixture
def storage() -> FakeAssetStorage:
    return FakeAssetStorage()


def test_associates_each_image_with_its_presentation_and_keeps_ids_and_uris(storage) -> None:
    product, box, unit = uuid4(), uuid4(), uuid4()
    first, second = _image(storage, product), _image(storage, product, is_primary=False)
    images = [first, second]
    snapshot = [(image.id, image.storage_uri) for image in images]

    plan = tool.build_plan(images, {box: product, unit: product}, _mapping({first.id: box, second.id: unit}),
                           storage, BUCKET)

    assert plan.ok
    assert [row.result for row in plan.rows] == [tool.ASSOCIATE, tool.ASSOCIATE]
    assert [row.global_product_presentation_id for row in plan.rows] == [str(box), str(unit)]
    # Caso 34b: la secundaria queda sola en su presentación y pasa a principal.
    assert [row.is_primary_after for row in plan.rows] == [True, True]
    # Casos 27 y 28: el plan no toca ids ni storage_uri, y solo lee metadatos (HEAD).
    assert [(image.id, image.storage_uri) for image in images] == snapshot
    assert set(storage.calls) == {"head"}


def test_presentation_with_several_images_keeps_its_primary(storage) -> None:
    product, box = uuid4(), uuid4()
    primary, secondary = _image(storage, product), _image(storage, product, is_primary=False)
    inactive = _image(storage, product, is_primary=False, status="INACTIVE")

    plan = tool.build_plan([primary, secondary, inactive], {box: product},
                           _mapping({primary.id: box, secondary.id: box, inactive.id: box}), storage, BUCKET)

    assert plan.ok
    assert [row.is_primary_after for row in plan.rows] == [True, False, False]


def test_indeterminate_primary_blocks(storage) -> None:
    product, box = uuid4(), uuid4()
    first, second = _image(storage, product, is_primary=False), _image(storage, product, is_primary=False)

    plan = tool.build_plan([first, second], {box: product}, _mapping({first.id: box, second.id: box}), storage, BUCKET)

    assert not plan.ok
    assert {row.cause for row in plan.blocking} == {tool.INDETERMINATE_PRIMARY}


@pytest.mark.parametrize(
    ("case", "cause"),
    [
        ("no_mapping", tool.NO_MAPPING),
        ("missing_presentation", tool.PRESENTATION_MISSING),
        ("other_product", tool.PRESENTATION_OF_OTHER_PRODUCT),
        ("product_contradicts", tool.SOURCES_CONTRADICT),
        ("uri_contradicts", tool.SOURCES_CONTRADICT),
        ("already_elsewhere", tool.ASSOCIATED_TO_OTHER),
        ("external_uri", tool.NOT_SHA_KEY),
        ("object_missing", tool.OBJECT_MISSING),
        ("sha_mismatch", tool.SHA_MISMATCH),
        ("storage_down", tool.STORAGE_UNAVAILABLE),
    ],
)
def test_single_inconsistent_case_blocks_the_whole_plan(storage, case, cause) -> None:
    """Caso 34: un solo caso ambiguo o inconsistente detiene el relleno y queda con su causa."""
    product, other_product, box, other_box = uuid4(), uuid4(), uuid4(), uuid4()
    good = _image(storage, product)
    bad = _image(storage, product, is_primary=False)
    presentations = {box: product, other_box: other_product}
    pairs = {good.id: box, bad.id: box}
    extra = {}
    if case == "no_mapping":
        del pairs[bad.id]
    elif case == "missing_presentation":
        pairs[bad.id] = uuid4()
    elif case == "other_product":
        pairs[bad.id] = other_box
    elif case == "product_contradicts":
        extra["product_by_asset"] = {bad.id: other_product}
    elif case == "uri_contradicts":
        extra["storage_uri_by_asset"] = {bad.id: f"s3://{BUCKET}/assets/{'0' * 64}.png"}
    elif case == "already_elsewhere":
        bad.global_product_presentation_id = uuid4()
    elif case == "external_uri":
        bad.storage_uri = "https://cdn.example.com/frente.png"
    elif case == "object_missing":
        storage.objects.pop(bad.storage_uri.split("/", 3)[3])
    elif case == "sha_mismatch":
        bad.storage_uri = _stored(storage, "otro", metadata_sha="f" * 64)
    elif case == "storage_down":
        storage.unavailable = True

    plan = tool.build_plan([good, bad], presentations, _mapping(pairs, **extra), storage, BUCKET)

    assert not plan.ok
    assert cause in {row.cause for row in plan.blocking}
    assert next(row for row in plan.rows if row.asset_id == str(bad.id)).cause == cause


def test_already_associated_images_are_idempotent(storage) -> None:
    product, box = uuid4(), uuid4()
    image = _image(storage, product)
    image.global_product_presentation_id = box
    storage.calls.clear()

    plan = tool.build_plan([image], {box: product}, _mapping({image.id: box}), storage, BUCKET)

    assert plan.ok and plan.rows[0].result == tool.ALREADY_ASSOCIATED and plan.rows[0].is_primary_after is True
    assert storage.calls == []  # lo ya asociado no se vuelve a consultar


def _write_csv(path: Path, rows: list[dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_mapping_from_gold_uses_presentation_ref_and_journal(tmp_path) -> None:
    asset, presentation, product = uuid4(), uuid4(), uuid4()
    uri = f"s3://{BUCKET}/assets/{'a' * 64}.jpg"
    gold = _write_csv(tmp_path / "product_assets.csv", [
        {"product_asset_ref": "AST-1", "product_ref": "PRD-1", "asset_type": "IMAGE", "storage_uri": uri,
         "product_presentation_ref": "PRS-1-BOX"},
        {"product_asset_ref": "AST-2", "product_ref": "PRD-1", "asset_type": "IMAGE", "storage_uri": uri,
         "product_presentation_ref": ""},
        {"product_asset_ref": "AST-3", "product_ref": "PRD-1", "asset_type": "IMAGE", "storage_uri": uri,
         "product_presentation_ref": "PRS-1-BOX"},
        {"product_asset_ref": "AST-4", "product_ref": "PRD-1", "asset_type": "TECHNICAL_SHEET", "storage_uri": uri,
         "product_presentation_ref": ""},
    ])
    journal = _write_csv(tmp_path / "sio_ids.csv", [
        {"csv": "product_assets", "ref": "AST-1", "sio_id": str(asset), "resultado": "CREADO", "ejecucion": "1"},
        {"csv": "product_assets", "ref": "AST-2", "sio_id": str(uuid4()), "resultado": "CREADO", "ejecucion": "1"},
        {"csv": "product_presentations", "ref": "PRS-1-BOX", "sio_id": str(presentation), "resultado": "CREADO",
         "ejecucion": "1"},
        {"csv": "products", "ref": "PRD-1", "sio_id": str(product), "resultado": "CREADO", "ejecucion": "1"},
    ])

    mapping = tool.mapping_from_gold(gold, journal)

    assert mapping.presentation_by_asset == {asset: presentation}
    assert mapping.product_by_asset == {asset: product}
    assert mapping.storage_uri_by_asset == {asset: uri}
    assert mapping.issues == {"AST-2": tool.NO_MAPPING, "AST-3": tool.ASSET_NOT_IN_JOURNAL}


def test_source_issues_block_the_plan(storage) -> None:
    product, box = uuid4(), uuid4()
    image = _image(storage, product)

    plan = tool.build_plan([image], {box: product}, _mapping({image.id: box}, issues={"AST-9": tool.NO_MAPPING}),
                           storage, BUCKET)

    assert not plan.ok and plan.source_issues == {"AST-9": tool.NO_MAPPING}


def test_report_has_no_bucket_keys_or_uris_and_includes_repeatable_sql(storage, tmp_path) -> None:
    """Caso 34c."""
    product, box = uuid4(), uuid4()
    image = _image(storage, product, is_primary=False)
    mapping = _mapping({image.id: box})
    plan = tool.build_plan([image], {box: product}, mapping, storage, BUCKET)

    data = tool.report("plan", "20261023T000000Z", mapping, plan, {"images_total": 1}, None)
    json_path, csv_path = tool.write_report(data, tmp_path)

    text = json_path.read_text(encoding="utf-8") + csv_path.read_text(encoding="utf-8")
    key = image.storage_uri.split("/", 3)[3]
    for secret in (BUCKET, key, "s3://", key.split("/")[1].split(".")[0]):
        assert secret not in text
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["ok"] is True
    assert loaded["summary"]["promoted_to_primary"] == 1
    assert set(loaded["repeatable_checks_sql"]) == set(tool.COUNT_QUERIES)
    assert all(query.lstrip().upper().startswith("SELECT") for query in tool.COUNT_QUERIES.values())
    assert csv_path.read_text(encoding="utf-8").splitlines()[0].startswith("asset_id,")
