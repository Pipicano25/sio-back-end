"""Carga inicial idempotente (RC-15, Principio XIV, FR-072)."""

from sqlalchemy import func, select

from product_catalog_service.infrastructure.models import (
    GlobalPackagingTypeModel,
    GlobalProductGroupTypeModel,
    GlobalUnitOfMeasureModel,
)
from product_catalog_service.seed.constants import SEED_ACTOR
from product_catalog_service.seed.loader import load_seed

MODELS = (GlobalUnitOfMeasureModel, GlobalPackagingTypeModel, GlobalProductGroupTypeModel)


def _snapshot(session) -> dict:
    return {
        model.__tablename__: sorted(
            (row.code, row.version, row.updated_at, row.status, row.name)
            for row in session.execute(select(model)).scalars()
        )
        for model in MODELS
    }


def test_first_load_creates_base_catalogs(session_factory) -> None:
    with session_factory() as session:
        results = load_seed(session)

    assert [(result.table, result.inserted) for result in results] == [
        ("global_units_of_measure", 8),
        ("global_packaging_types", 10),
        ("global_product_group_types", 15),
    ]

    with session_factory() as session:
        creators = set(session.execute(select(GlobalUnitOfMeasureModel.created_by)).scalars())
        updaters = set(session.execute(select(GlobalProductGroupTypeModel.updated_by)).scalars())
        group_1 = session.execute(
            select(GlobalProductGroupTypeModel).where(GlobalProductGroupTypeModel.code == "GROUP_1")
        ).scalar_one()

    assert creators == {SEED_ACTOR}
    assert updaters == {SEED_ACTOR}
    assert group_1.allows_multiple is False


def test_second_load_changes_nothing(session_factory) -> None:
    with session_factory() as session:
        load_seed(session)
    with session_factory() as session:
        before = _snapshot(session)

    with session_factory() as session:
        results = load_seed(session)
    with session_factory() as session:
        after = _snapshot(session)

    assert all(result.inserted == 0 for result in results)
    assert before == after


def test_seed_does_not_reactivate_or_overwrite(session_factory) -> None:
    with session_factory() as session:
        load_seed(session)
        unit = session.execute(
            select(GlobalUnitOfMeasureModel).where(GlobalUnitOfMeasureModel.code == "KG")
        ).scalar_one()
        unit.status = "INACTIVE"
        unit.name = "Kilo (renombrado)"
        session.commit()

    with session_factory() as session:
        load_seed(session)
        unit = session.execute(
            select(GlobalUnitOfMeasureModel).where(GlobalUnitOfMeasureModel.code == "KG")
        ).scalar_one()
        total = session.execute(select(func.count()).select_from(GlobalUnitOfMeasureModel)).scalar_one()

    assert unit.status == "INACTIVE"
    assert unit.name == "Kilo (renombrado)"
    assert total == 8
