"""Relleno de imágenes por presentación contra PostgreSQL (spec 024, casos 26, 27, 28, 33, 34 y 34b).

La base de pruebas está en la cabeza (0006, toda imagen exige presentación). Para reproducir la etapa de
transición, la prueba retira solo `ck_product_assets_image_requires_presentation` y la restaura al final, sobre
la base ya vaciada (como `downgrade`/`upgrade` de 0006).
"""

from __future__ import annotations

import hashlib
from uuid import UUID

import pytest
from sqlalchemy import select, text

from product_catalog_service.audit_context import AuditActor, reset_actor, set_actor
from product_catalog_service.infrastructure.models import ProductAssetModel
from product_catalog_service.tools import migrate_presentation_images as tool
from tests import factories
from tests.conftest import truncate_all
from tests.spec022_support import image_asset
from tests.storage_fakes import BUCKET, FakeAssetStorage

CHECK = "ck_product_assets_image_requires_presentation"


@pytest.fixture
def transition_schema(test_engine, clean_database):
    with test_engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE product_assets DROP CONSTRAINT {CHECK}"))
    try:
        yield
    finally:
        truncate_all(test_engine)
        with test_engine.begin() as connection:
            connection.execute(text(
                f"ALTER TABLE product_assets ADD CONSTRAINT {CHECK} "
                "CHECK (asset_type <> 'IMAGE' OR global_product_presentation_id IS NOT NULL)"))


@pytest.fixture
def actor():
    token = set_actor(AuditActor(tool.ACTOR_SUBJECT, tool.ACTOR_USERNAME))
    yield
    reset_actor(token)


@pytest.fixture
def storage() -> FakeAssetStorage:
    return FakeAssetStorage()


def _legacy_image(session_factory, storage, product_id, label: str, *, is_primary=True, status="ACTIVE"):
    content = label.encode()
    sha = hashlib.sha256(content).hexdigest()
    storage.put(f"assets/{sha}.png", content, content_type="image/png", metadata={"sha256": sha})
    return image_asset(session_factory, product_id, content=content, is_primary=is_primary, status=status,
                       presentation_id=None)


@pytest.fixture
def legacy(transition_schema, session_factory, storage):
    """Dos productos: uno con imagen principal y otro con una secundaria (como las 8 del Gold)."""
    unit = factories.unit(session_factory)
    first = factories.product(session_factory, unit.id, name="Producto con principal")
    second = factories.product(session_factory, unit.id, name="Producto con secundaria")
    box = factories.presentation(session_factory, first.id, "BOX")
    blister = factories.presentation(session_factory, second.id, "BLISTER")
    primary = _legacy_image(session_factory, storage, first.id, "frente")
    secondary = _legacy_image(session_factory, storage, second.id, "lateral", is_primary=False)
    return {"primary": primary, "secondary": secondary, "box": box, "blister": blister,
            "mapping": tool.Mapping({primary.id: box.id, secondary.id: blister.id})}


def _state(session_factory) -> list[tuple]:
    with session_factory() as session:
        return [(a.id, a.storage_uri, a.global_product_presentation_id, a.is_primary, a.status, a.version)
                for a in session.scalars(select(ProductAssetModel).order_by(ProductAssetModel.id))]


def test_plan_writes_nothing(legacy, session_factory, storage) -> None:
    """Caso 33 (simulación)."""
    before = _state(session_factory)
    with session_factory() as session:
        images = tool._images(session)
        plan = tool.build_plan(images, tool._presentations(session, legacy["mapping"].presentation_by_asset.values()),
                               legacy["mapping"], storage, BUCKET)
        session.rollback()

    assert plan.ok and [row.result for row in plan.rows].count(tool.ASSOCIATE) == 2
    assert _state(session_factory) == before
    assert set(storage.calls) == {"head"}


def test_apply_associates_keeps_ids_uris_and_sets_one_primary_per_presentation(
    legacy, session_factory, storage, actor, outbox
) -> None:
    """Casos 26, 27, 28 y 34b."""
    before = {row[0]: row for row in _state(session_factory)}
    objects = dict(storage.objects)

    with session_factory() as session:
        plan = tool.apply(session, legacy["mapping"], storage, BUCKET, run_id="prueba")
        after_counts = tool.counts(session)

    assert plan.ok
    after = {row[0]: row for row in _state(session_factory)}
    assert set(after) == set(before)  # ids conservados
    assert all(after[i][1] == before[i][1] for i in after)  # storage_uri conservados
    assert after[legacy["primary"].id][2:4] == (legacy["box"].id, True)
    assert after[legacy["secondary"].id][2:4] == (legacy["blister"].id, True)  # la secundaria pasa a principal
    assert storage.objects == objects and set(storage.calls) == {"head"}  # sin borrar ni volver a subir
    assert after_counts["images_without_presentation"] == 0
    assert after_counts["presentations_with_primary_image"] == 2
    assert after_counts["presentations_with_two_or_more_primaries"] == 0

    events = [e for e in outbox() if e["action"] == "UPDATE_PRODUCT_ASSET"]
    assert len(events) == 2
    assert {e["entity_id"] for e in events} == {str(legacy["primary"].id), str(legacy["secondary"].id)}
    assert all(e["username_snapshot"] == tool.ACTOR_USERNAME for e in events)
    assert all(e["new_values"].keys() >= {"global_product_presentation_id"} for e in events)
    assert all("prueba" in e["reason"] for e in events)

    with session_factory() as session:
        verification = tool.verify_result(session, legacy["mapping"], storage, BUCKET)
    assert verification["errors"] == []


def test_apply_is_idempotent(legacy, session_factory, storage, actor, outbox) -> None:
    """Caso 33 (repetición)."""
    with session_factory() as session:
        tool.apply(session, legacy["mapping"], storage, BUCKET, run_id="primera")
    once = _state(session_factory)
    events = len(outbox())

    with session_factory() as session:
        plan = tool.apply(session, legacy["mapping"], storage, BUCKET, run_id="segunda")

    assert {row.result for row in plan.rows} == {tool.ALREADY_ASSOCIATED}
    assert _state(session_factory) == once
    assert len(outbox()) == events


def test_single_ambiguous_case_blocks_without_changes(legacy, session_factory, storage, actor, outbox) -> None:
    """Caso 34: falta el objeto de una sola imagen y nada se aplica."""
    before = _state(session_factory)
    storage.objects.pop(legacy["secondary"].storage_uri.split("/", 3)[3])

    with session_factory() as session, pytest.raises(tool.MigrationBlocked) as blocked:
        tool.apply(session, legacy["mapping"], storage, BUCKET, run_id="bloqueada")

    assert _state(session_factory) == before
    assert [(row.asset_id, row.cause) for row in blocked.value.plan.blocking] == [
        (str(legacy["secondary"].id), tool.OBJECT_MISSING)]
    assert outbox() == []


def test_indeterminate_primary_blocks_without_changes(transition_schema, session_factory, storage, actor) -> None:
    """Caso 34b: dos imágenes no principales para una presentación detienen el relleno."""
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id)
    box = factories.presentation(session_factory, product.id, "BOX")
    first = _legacy_image(session_factory, storage, product.id, "uno", is_primary=False)
    second = _legacy_image(session_factory, storage, product.id, "dos", is_primary=False)
    before = _state(session_factory)

    with session_factory() as session, pytest.raises(tool.MigrationBlocked) as blocked:
        tool.apply(session, tool.Mapping({first.id: box.id, second.id: box.id}), storage, BUCKET, run_id="x")

    assert {row.cause for row in blocked.value.plan.blocking} == {tool.INDETERMINATE_PRIMARY}
    assert _state(session_factory) == before


def test_verify_reports_images_without_presentation(legacy, session_factory, storage) -> None:
    with session_factory() as session:
        verification = tool.verify_result(session, legacy["mapping"], storage, BUCKET)

    causes = {error["cause"] for error in verification["errors"]}
    assert {"WITHOUT_PRESENTATION", "COUNT_NOT_ZERO"} <= causes
    assert isinstance(next(iter(legacy["mapping"].presentation_by_asset)), UUID)
