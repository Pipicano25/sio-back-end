"""Concurrencia por presentación (spec 024, caso 22; FR-024-26).

Operaciones simultáneas sobre la misma presentación con sesiones independientes de la base de pruebas: nunca
quedan dos principales y ninguna operación pierde un cambio.
"""

from __future__ import annotations

import threading

import pytest
from sqlalchemy import text

from product_catalog_service.application.exceptions import DomainError
from product_catalog_service.application.presentation_image_service import PresentationImageService
from product_catalog_service.domain.image_upload import validate_image
from tests import factories, images
from tests.api.test_asset_content_api import FakeAssetStorage
from tests.spec022_support import BUCKET

LIMITS = {"max_bytes": 5_242_880, "max_pixels": 40_000_000}


@pytest.fixture
def setup(session_factory):
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, "Gaseosa cola")
    bottle = factories.presentation(session_factory, product.id, "BOTELLA600")
    return product, bottle, FakeAssetStorage()


def run_concurrently(*operations):
    barrier = threading.Barrier(len(operations))
    results: list = [None] * len(operations)

    def worker(index, operation):
        barrier.wait()
        try:
            results[index] = operation()
        except DomainError as exc:
            results[index] = exc

    threads = [threading.Thread(target=worker, args=(i, op)) for i, op in enumerate(operations)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


OPEN_SESSIONS: list = []


@pytest.fixture(autouse=True)
def close_sessions(session_factory):
    yield
    while OPEN_SESSIONS:
        OPEN_SESSIONS.pop().close()


def service(session_factory, storage):
    session = session_factory()
    OPEN_SESSIONS.append(session)  # como `get_db_session`: se cierra al terminar la solicitud
    return PresentationImageService(session, bucket=BUCKET, storage=storage)


def primaries(session_factory, presentation_id) -> int:
    with session_factory() as session:
        return session.execute(
            text("SELECT count(*) FROM product_assets WHERE global_product_presentation_id = :p "
                 "AND is_primary AND status = 'ACTIVE'"), {"p": presentation_id}).scalar_one()


def test_simultaneous_uploads_of_different_content_leave_one_primary(session_factory, setup) -> None:
    product, bottle, storage = setup
    first = validate_image(images.png((1, 1, 1)), **LIMITS)
    second = validate_image(images.png((2, 2, 2)), **LIMITS)

    results = run_concurrently(
        lambda: service(session_factory, storage).upload(product.id, bottle.id, first, file_name="a.png", actor="a"),
        lambda: service(session_factory, storage).upload(product.id, bottle.id, second, file_name="b.png", actor="b"),
    )

    assert all(isinstance(result, tuple) and result[1] is True for result in results), results
    assert primaries(session_factory, bottle.id) == 1


def test_simultaneous_uploads_of_same_content_create_one_and_reject_the_other(session_factory, setup) -> None:
    product, bottle, storage = setup
    image = validate_image(images.png(), **LIMITS)

    results = run_concurrently(
        lambda: service(session_factory, storage).upload(product.id, bottle.id, image, file_name="a.png", actor="a"),
        lambda: service(session_factory, storage).upload(product.id, bottle.id, image, file_name="b.png", actor="b"),
    )

    codes = sorted(result.code if isinstance(result, DomainError) else "CREATED" for result in results)
    assert codes == ["CREATED", "DUPLICATE_ASSET_CONTENT"]
    with session_factory() as session:
        assert session.execute(text("SELECT count(*) FROM product_assets")).scalar_one() == 1


def test_simultaneous_set_primary_and_deactivate_are_serialized(session_factory, setup) -> None:
    product, bottle, storage = setup
    created = [
        service(session_factory, storage).upload(
            product.id, bottle.id, validate_image(images.png((n, n, n)), **LIMITS), file_name="x.png", actor="t"
        )[0]
        for n in (1, 2, 3)
    ]
    first, second, third = created  # third es la principal
    with session_factory() as session:
        versions = dict(session.execute(text("SELECT id, version FROM product_assets")).all())

    results = run_concurrently(
        lambda: service(session_factory, storage).set_primary(product.id, bottle.id, first.id,
                                                              version=versions[first.id], actor="a"),
        lambda: service(session_factory, storage).deactivate(product.id, bottle.id, third.id,
                                                             version=versions[third.id], actor="b"),
    )

    assert not any(isinstance(result, DomainError) and result.code != "VERSION_CONFLICT" for result in results)
    assert primaries(session_factory, bottle.id) == 1
    with session_factory() as session:
        status = session.execute(text("SELECT status FROM product_assets WHERE id = :id"), {"id": third.id}).scalar_one()
    assert status == "INACTIVE" or any(isinstance(result, DomainError) for result in results)
