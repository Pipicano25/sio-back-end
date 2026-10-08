"""Repositorio SQLAlchemy de sectores de una organización (FR-060–FR-065, R-05, R-05a)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from party_identity_service.application import audit_events as audit
from party_identity_service.application.exceptions import (
    DuplicateActiveSectorAssignmentError,
    InvalidPrimarySectorError,
    InvalidStatusTransitionError,
    NotFoundError,
    PrimarySectorConflictError,
    VersionConflictError,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.business_sector import OrganizationBusinessSector
from party_identity_service.domain.contact import RelationState
from party_identity_service.infrastructure.models import (
    OrganizationBusinessSectorModel as Model,
    OrganizationIdentityModel,
)
from party_identity_service.infrastructure.persistence import commit_or_translate, flush_or_translate

DUPLICATES = {
    "uq_organization_business_sectors_active": DuplicateActiveSectorAssignmentError,
    "uq_organization_business_sectors_primary": PrimarySectorConflictError,
}


def closing_instant(valid_from: datetime, now: datetime) -> datetime:
    """Fin de vigencia `[valid_from, valid_to)` al cerrar (R-05a).

    Si la vigencia aún no inició, `valid_to = valid_from` (nunca estuvo vigente);
    si ya inició, el instante efectivo del cierre.
    """
    return valid_from if now < valid_from else now


def state_condition(model, state: RelationState):
    if state == "active":
        return model.is_active.is_(True)
    if state == "closed":
        return model.is_active.is_(False)
    return None


class SQLAlchemyOrganizationBusinessSectorRepository:
    """Persistencia de `organization_business_sectors`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_organization(
        self, organization_id: UUID, *, state: RelationState, page: int, page_size: int
    ) -> PageResult[OrganizationBusinessSector]:
        conditions = [Model.organization_identity_id == organization_id]
        condition = state_condition(Model, state)
        if condition is not None:
            conditions.append(condition)
        total = self.session.scalar(select(func.count()).select_from(Model).where(*conditions)) or 0
        models = self.session.scalars(
            select(Model)
            .where(*conditions)
            .order_by(Model.is_active.desc(), Model.is_primary.desc(), Model.valid_from.desc(), Model.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return PageResult(
            items=[self._to_domain(model) for model in models],
            page=page,
            page_size=page_size,
            total_records=total,
        )

    def get_by_id(self, assignment_id: UUID) -> OrganizationBusinessSector | None:
        model = self.session.get(Model, assignment_id)
        return self._to_domain(model) if model is not None else None

    def _lock_organization(self, organization_id: UUID) -> None:
        self.session.get(
            OrganizationIdentityModel,
            organization_id,
            with_for_update=True,
            populate_existing=True,
        )

    def _current_primary(self, organization_id: UUID, *, exclude: UUID | None = None):
        statement = select(Model).where(
            Model.organization_identity_id == organization_id,
            Model.is_active.is_(True),
            Model.is_primary.is_(True),
        )
        if exclude is not None:
            statement = statement.where(Model.id != exclude)
        return self.session.scalars(statement.execution_options(populate_existing=True)).first()

    def create(
        self,
        *,
        organization_id: UUID,
        sector_id: UUID,
        is_primary: bool,
        valid_from: datetime | None,
        actor_id: str,
    ) -> OrganizationBusinessSector:
        self._lock_organization(organization_id)
        if is_primary and self._current_primary(organization_id) is not None:
            self.session.rollback()
            raise PrimarySectorConflictError

        model = Model(
            organization_identity_id=organization_id,
            global_business_sector_id=sector_id,
            is_primary=is_primary,
            is_active=True,
            valid_from=valid_from or datetime.now(timezone.utc),
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.session.add(model)
        audit.track_create(self.session, model, action=audit.ASSIGN_ORGANIZATION_BUSINESS_SECTOR, entity_type="OrganizationBusinessSector")
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(model)
        return self._to_domain(model)

    def set_primary(
        self, assignment_id: UUID, *, expected_version: int, actor_id: str
    ) -> OrganizationBusinessSector:
        # Se obtiene la organización sin cargar la entidad, para no dejar en la sesión
        # una versión anterior al bloqueo.
        organization_id = self.session.scalar(
            select(Model.organization_identity_id).where(Model.id == assignment_id)
        )
        if organization_id is None:
            raise NotFoundError("La asignación de sector no existe.")

        self._lock_organization(organization_id)
        target = self.session.get(Model, assignment_id, with_for_update=True, populate_existing=True)

        if target.version != expected_version:
            self.session.rollback()
            raise VersionConflictError
        if not target.is_active:
            self.session.rollback()
            raise InvalidPrimarySectorError
        if target.is_primary:
            self.session.rollback()
            return self._to_domain(target)

        previous = self._current_primary(organization_id, exclude=assignment_id)
        if previous is not None:
            previous.is_primary = False
            previous.updated_by = actor_id
            flush_or_translate(self.session, duplicates=DUPLICATES)

        target.is_primary = True
        target.updated_by = actor_id
        audit.track_update(self.session, target, action=audit.SET_PRIMARY_ORGANIZATION_BUSINESS_SECTOR, entity_type="OrganizationBusinessSector", extra_previous={"previous_primary_id": previous.id if previous is not None else None})
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(target)
        return self._to_domain(target)

    def close(
        self, assignment_id: UUID, *, expected_version: int, actor_id: str
    ) -> OrganizationBusinessSector:
        target = self.session.get(Model, assignment_id, with_for_update=True, populate_existing=True)
        if target is None:
            self.session.rollback()
            raise NotFoundError("La asignación de sector no existe.")
        if target.version != expected_version:
            self.session.rollback()
            raise VersionConflictError
        if not target.is_active:
            self.session.rollback()
            raise InvalidStatusTransitionError("La asignación ya está cerrada; no se reactiva.")

        target.is_active = False
        target.is_primary = False
        target.valid_to = closing_instant(target.valid_from, datetime.now(timezone.utc))
        target.updated_by = actor_id
        audit.track_update(self.session, target, action=audit.CLOSE_ORGANIZATION_BUSINESS_SECTOR, entity_type="OrganizationBusinessSector")
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(target)
        return self._to_domain(target)

    @staticmethod
    def _to_domain(model: Model) -> OrganizationBusinessSector:
        return OrganizationBusinessSector(
            id=model.id,
            organization_identity_id=model.organization_identity_id,
            global_business_sector_id=model.global_business_sector_id,
            is_primary=model.is_primary,
            is_active=model.is_active,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
