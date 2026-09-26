"""Restricciones de grupos y asignaciones (RC-02)."""

import pytest
from sqlalchemy.exc import IntegrityError

from product_catalog_service.infrastructure.models import (
    GlobalProductGroupModel,
    GlobalProductGroupTypeModel,
)
from tests import factories


def _type(session_factory, code: str):
    return factories._save(session_factory, GlobalProductGroupTypeModel(code=code, name=code))


def _group(session_factory, type_id, code: str, parent=None):
    return factories._save(
        session_factory,
        GlobalProductGroupModel(group_type_id=type_id, code=code, name=code, parent_group_id=parent),
    )


def test_parent_must_be_same_type(session_factory) -> None:
    first = _type(session_factory, "GROUP_1")
    second = _type(session_factory, "GROUP_2")
    parent = _group(session_factory, first.id, "PADRE")

    with pytest.raises(IntegrityError, match="fk_global_product_groups_parent_same_type"):
        _group(session_factory, second.id, "HIJO", parent=parent.id)


def test_code_unique_within_type(session_factory) -> None:
    first = _type(session_factory, "GROUP_1")
    second = _type(session_factory, "GROUP_2")
    _group(session_factory, first.id, "ALIMENTOS")
    _group(session_factory, second.id, "ALIMENTOS")

    with pytest.raises(IntegrityError, match="uq_global_product_groups_type_code"):
        _group(session_factory, first.id, "ALIMENTOS")


def test_not_self_parent(session_factory) -> None:
    group_type = _type(session_factory, "GROUP_1")
    group = _group(session_factory, group_type.id, "A")

    with session_factory() as session:
        stored = session.get(GlobalProductGroupModel, group.id)
        stored.parent_group_id = stored.id
        with pytest.raises(IntegrityError, match="ck_global_product_groups_not_self_parent"):
            session.commit()


def test_assignment_pair_unique(session_factory) -> None:
    from product_catalog_service.infrastructure.models import GlobalProductGroupAssignmentModel

    group_type = _type(session_factory, "GROUP_1")
    group = _group(session_factory, group_type.id, "A")
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id)

    def assign():
        return factories._save(
            session_factory,
            GlobalProductGroupAssignmentModel(
                global_product_id=product.id,
                global_product_group_id=group.id,
                group_type_id=group_type.id,
            ),
        )

    assign()
    with pytest.raises(IntegrityError, match="uq_global_product_group_assignments_product_group"):
        assign()
