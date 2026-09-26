"""Asignaciones simultáneas con `allows_multiple = FALSE` (RC-08, R-10)."""

import threading

from product_catalog_service.application.exceptions import DomainError
from product_catalog_service.application.group_assignment_service import GroupAssignmentService
from product_catalog_service.infrastructure.models import (
    GlobalProductGroupAssignmentModel,
    GlobalProductGroupModel,
    GlobalProductGroupTypeModel,
)
from tests import factories


def test_only_one_assignment_per_single_value_type(session_factory) -> None:
    group_type = factories._save(session_factory, GlobalProductGroupTypeModel(code="GROUP_1", name="Grupo 1"))
    groups = [
        factories._save(
            session_factory,
            GlobalProductGroupModel(group_type_id=group_type.id, code=code, name=code),
        )
        for code in ("A", "B")
    ]
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def assign(group_id) -> None:
        with session_factory() as session:
            barrier.wait()
            try:
                GroupAssignmentService(session).assign(product.id, group_id, "t")
                outcomes.append("ok")
            except DomainError as exc:
                outcomes.append(exc.code)

    threads = [threading.Thread(target=assign, args=(group.id,)) for group in groups]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["GROUP_TYPE_SINGLE_VALUE", "ok"]
    with session_factory() as session:
        assert session.query(GlobalProductGroupAssignmentModel).filter_by(status="ACTIVE").count() == 1
