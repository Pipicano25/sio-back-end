"""Consultas jerárquicas y restricciones de categorías (RC-02)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from product_catalog_service.infrastructure.hierarchy_repository import HierarchyRepository
from product_catalog_service.infrastructure.models import GlobalCategoryModel


def _category(session: Session, code: str, parent: UUID | None = None, status: str = "ACTIVE") -> UUID:
    now = datetime.now(UTC)
    entity = GlobalCategoryModel(
        code=code,
        name=code.title(),
        parent_category_id=parent,
        status=status,
        created_at=now,
        updated_at=now,
        created_by="t",
        updated_by="t",
    )
    session.add(entity)
    session.flush()
    return entity.id


def test_self_parent_check(db_session: Session) -> None:
    category_id = _category(db_session, "ALIMENTOS")
    with pytest.raises(IntegrityError, match="ck_global_categories_not_self_parent"):
        db_session.execute(
            text("UPDATE global_categories SET parent_category_id = id WHERE id = :id"),
            {"id": category_id},
        )


def test_ancestors_descendants_and_children(db_session: Session) -> None:
    alimentos = _category(db_session, "ALIMENTOS")
    granos = _category(db_session, "GRANOS", alimentos)
    arroz = _category(db_session, "ARROZ", granos)
    integral = _category(db_session, "ARROZ_INTEGRAL", arroz)
    _category(db_session, "BEBIDAS")

    tree = HierarchyRepository(db_session, GlobalCategoryModel, "parent_category_id")

    assert [c.code for c in tree.ancestors(integral)] == ["ALIMENTOS", "GRANOS", "ARROZ", "ARROZ_INTEGRAL"]
    descendants = {c.code for c in db_session.execute(tree.descendants_statement(alimentos)).scalars()}
    assert descendants == {"GRANOS", "ARROZ", "ARROZ_INTEGRAL"}
    assert set(tree.descendant_ids_including(granos)) == {granos, arroz, integral}
    assert tree.parent_of(arroz) == granos
    assert tree.has_active_children(granos)
    assert not tree.has_active_children(integral)


def test_inactive_children_do_not_count(db_session: Session) -> None:
    root = _category(db_session, "ROOT")
    _category(db_session, "CHILD", root, status="INACTIVE")
    tree = HierarchyRepository(db_session, GlobalCategoryModel, "parent_category_id")
    assert not tree.has_active_children(root)
    assert tree.ancestors(uuid4()) == []
