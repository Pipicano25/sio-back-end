"""Registros simultáneos de primer uso producen una sola marca (R-10, R-15)."""

import threading

from product_catalog_service.application.first_use_service import FirstUseService
from product_catalog_service.infrastructure.models import GlobalProductModel
from tests import factories


def test_concurrent_registrations_single_mark(session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)
    barrier = threading.Barrier(2)
    results: list = []

    def register(actor: str) -> None:
        with session_factory() as session:
            barrier.wait()
            result = FirstUseService(session).register_adoption(product.id, None, actor)
            results.append((result.product.first_used_at, result.product.first_used_by))

    threads = [threading.Thread(target=register, args=(actor,)) for actor in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with session_factory() as session:
        stored = session.get(GlobalProductModel, product.id)
        assert stored.version == product.version + 1
        assert {actor for _, actor in results} == {stored.first_used_by}
        assert len(results) == 2
