"""Carga inicial idempotente (FR-072, Principio XIV, D2).

`INSERT … ON CONFLICT (code) DO NOTHING`: una ejecución repetida no crea
duplicados ni sobrescribe o reactiva registros modificados por un administrador.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from product_catalog_service.infrastructure.models import (
    GlobalPackagingTypeModel,
    GlobalProductGroupTypeModel,
    GlobalUnitOfMeasureModel,
)
from product_catalog_service.seed.constants import SEED_ACTOR
from product_catalog_service.seed.data import GROUP_TYPES, PACKAGING_TYPES, UNITS


@dataclass(frozen=True, slots=True)
class SeedResult:
    table: str
    inserted: int
    skipped: int


def _load(session: Session, model, rows) -> SeedResult:
    now = datetime.now(UTC)
    values = [
        {
            **row,
            "id": uuid4(),
            "status": "ACTIVE",
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "created_by": SEED_ACTOR,
            "updated_by": SEED_ACTOR,
        }
        for row in rows
    ]
    statement = (
        insert(model)
        .values(values)
        .on_conflict_do_nothing(index_elements=["code"])
        .returning(model.id)
    )
    inserted = len(session.execute(statement).all())
    return SeedResult(model.__tablename__, inserted, len(values) - inserted)


def load_seed(session: Session) -> list[SeedResult]:
    """Carga unidades, tipos de empaque y tipos de grupo en una transacción."""
    results = [
        _load(session, GlobalUnitOfMeasureModel, UNITS),
        _load(session, GlobalPackagingTypeModel, PACKAGING_TYPES),
        _load(session, GlobalProductGroupTypeModel, GROUP_TYPES),
    ]
    session.commit()
    return results
