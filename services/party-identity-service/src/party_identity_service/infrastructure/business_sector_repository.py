"""Repositorio SQLAlchemy del catálogo de sectores económicos (FR-050–FR-058)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, or_, select, text
from sqlalchemy.orm import Session

from party_identity_service.application.exceptions import DuplicateSectorCodeError
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.business_sector import BusinessSector, SectorStatus
from party_identity_service.infrastructure.models import GlobalBusinessSectorModel as Model
from party_identity_service.infrastructure.persistence import (
    commit_or_translate,
    load_for_update,
)

DUPLICATES = {"uq_global_business_sectors_system_code": DuplicateSectorCodeError}


@dataclass(frozen=True, slots=True)
class SectorSeedRow:
    """Fila del snapshot CIIU lista para cargar (padres antes que hijos)."""

    code: str
    name: str
    parent_code: str | None


@dataclass(frozen=True, slots=True)
class SeedResult:
    created: int
    updated: int
    unchanged: int


class SQLAlchemyBusinessSectorRepository:
    """Persistencia de `global_business_sectors`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        classification_system: str | None = None,
        code: str | None = None,
        parent_sector_id: UUID | None = None,
        roots_only: bool = False,
        status: SectorStatus = "ACTIVE",
        search: str | None = None,
    ) -> PageResult[BusinessSector]:
        conditions = [Model.status == status]
        if classification_system is not None:
            conditions.append(Model.classification_system == classification_system)
        if code is not None:
            conditions.append(Model.code == code)
        if parent_sector_id is not None:
            conditions.append(Model.parent_sector_id == parent_sector_id)
        if roots_only:
            conditions.append(Model.parent_sector_id.is_(None))
        if search:
            pattern = f"%{search}%"
            conditions.append(or_(Model.code.ilike(pattern), Model.name.ilike(pattern)))

        total = self.session.scalar(select(func.count()).select_from(Model).where(*conditions)) or 0
        models = self.session.scalars(
            select(Model)
            .where(*conditions)
            .order_by(Model.classification_system, Model.code)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return PageResult(
            items=[self._to_domain(model) for model in models],
            page=page,
            page_size=page_size,
            total_records=total,
        )

    def get_by_id(self, sector_id: UUID) -> BusinessSector | None:
        model = self.session.get(Model, sector_id)
        return self._to_domain(model) if model is not None else None

    def create(
        self,
        *,
        parent_sector_id: UUID | None,
        classification_system: str,
        code: str,
        name: str,
        description: str | None,
        actor_id: str,
    ) -> BusinessSector:
        model = Model(
            parent_sector_id=parent_sector_id,
            classification_system=classification_system,
            code=code,
            name=name,
            description=description,
            status="ACTIVE",
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.session.add(model)
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(model)
        return self._to_domain(model)

    def update(
        self, sector_id: UUID, *, expected_version: int, values: dict[str, Any], actor_id: str
    ) -> BusinessSector:
        model = load_for_update(
            self.session,
            Model,
            sector_id,
            expected_version=expected_version,
            not_found_message="El sector no existe.",
        )
        for field, value in values.items():
            setattr(model, field, value)
        model.updated_by = actor_id
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(model)
        return self._to_domain(model)

    def has_active_children(self, sector_id: UUID) -> bool:
        return bool(
            self.session.scalar(
                select(
                    exists().where(Model.parent_sector_id == sector_id, Model.status == "ACTIVE")
                )
            )
        )

    def ancestor_ids(self, sector_id: UUID) -> list[UUID]:
        """Ancestros de `sector_id` (incluido él mismo), con CTE recursiva."""
        rows = self.session.execute(
            text(
                "WITH RECURSIVE chain(id, parent_sector_id, depth) AS ("
                " SELECT id, parent_sector_id, 0 FROM global_business_sectors WHERE id = :id"
                " UNION ALL"
                " SELECT s.id, s.parent_sector_id, c.depth + 1 FROM global_business_sectors s"
                " JOIN chain c ON s.id = c.parent_sector_id WHERE c.depth < 64"
                ") SELECT id FROM chain"
            ),
            {"id": sector_id},
        ).scalars().all()
        return list(rows)

    # -- carga inicial (seed) -------------------------------------------------------

    def upsert_catalog(
        self,
        *,
        classification_system: str,
        rows: list[SectorSeedRow],
        actor_id: str,
    ) -> SeedResult:
        """Carga idempotente por (`classification_system`, `code`) en UNA transacción.

        Conserva los UUID existentes; solo actualiza `name` o el padre si
        difieren. Confirma al final; ante cualquier error revierte todo.
        """
        existing = {
            model.code: model
            for model in self.session.scalars(
                select(Model).where(Model.classification_system == classification_system)
            ).all()
        }
        created = updated = unchanged = 0

        try:
            for row in rows:
                parent_id = existing[row.parent_code].id if row.parent_code else None
                model = existing.get(row.code)
                if model is None:
                    model = Model(
                        parent_sector_id=parent_id,
                        classification_system=classification_system,
                        code=row.code,
                        name=row.name,
                        status="ACTIVE",
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                    self.session.add(model)
                    self.session.flush()
                    existing[row.code] = model
                    created += 1
                elif model.name != row.name or model.parent_sector_id != parent_id:
                    model.name = row.name
                    model.parent_sector_id = parent_id
                    model.updated_by = actor_id
                    updated += 1
                else:
                    unchanged += 1
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return SeedResult(created=created, updated=updated, unchanged=unchanged)

    @staticmethod
    def _to_domain(model: Model) -> BusinessSector:
        return BusinessSector(
            id=model.id,
            parent_sector_id=model.parent_sector_id,
            classification_system=model.classification_system,
            code=model.code,
            name=model.name,
            description=model.description,
            status=model.status,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
