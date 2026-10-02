"""Repositorio SQLAlchemy de representantes legales (FR-070–FR-078, R-05, R-05a)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from party_identity_service.application.exceptions import (
    DuplicateActiveRepresentativeError,
    InvalidStatusTransitionError,
    NotFoundError,
    PrimaryRepresentativeConflictError,
    VersionConflictError,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.contact import RelationState
from party_identity_service.domain.legal_representative import (
    LegalRepresentative,
    RepresentativeType,
    is_primary_type,
)
from party_identity_service.infrastructure.models import (
    OrganizationIdentityModel,
    OrganizationLegalRepresentativeModel as Model,
)
from party_identity_service.infrastructure.organization_business_sector_repository import (
    closing_instant,
    state_condition,
)
from party_identity_service.infrastructure.persistence import (
    commit_or_translate,
    flush_or_translate,
    load_for_update,
)

DUPLICATES = {
    "uq_organization_legal_representatives_primary": PrimaryRepresentativeConflictError,
    "uq_organization_legal_representatives_person": DuplicateActiveRepresentativeError,
}


class SQLAlchemyLegalRepresentativeRepository:
    """Persistencia de `organization_legal_representatives`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_organization(
        self, organization_id: UUID, *, state: RelationState, page: int, page_size: int
    ) -> PageResult[LegalRepresentative]:
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

    def get_by_id(self, representative_id: UUID) -> LegalRepresentative | None:
        model = self.session.get(Model, representative_id)
        return self._to_domain(model) if model is not None else None

    def get_active_primary(self, organization_id: UUID) -> LegalRepresentative | None:
        model = self._active_primary_model(organization_id)
        return self._to_domain(model) if model is not None else None

    def _active_primary_model(self, organization_id: UUID):
        return self.session.scalars(
            select(Model)
            .where(
                Model.organization_identity_id == organization_id,
                Model.is_active.is_(True),
                Model.representative_type == "PRIMARY",
            )
            .execution_options(populate_existing=True)
        ).first()

    def _lock_organization(self, organization_id: UUID) -> None:
        self.session.get(
            OrganizationIdentityModel,
            organization_id,
            with_for_update=True,
            populate_existing=True,
        )

    def _new_model(
        self,
        *,
        organization_id: UUID,
        person_identity_id: UUID,
        representative_type: RepresentativeType,
        position: str | None,
        valid_from: datetime | None,
        source_document_reference: str | None,
        actor_id: str,
    ) -> Model:
        return Model(
            organization_identity_id=organization_id,
            person_identity_id=person_identity_id,
            representative_type=representative_type,
            position=position,
            is_primary=is_primary_type(representative_type),
            is_active=True,
            valid_from=valid_from or datetime.now(timezone.utc),
            source_document_reference=source_document_reference,
            created_by=actor_id,
            updated_by=actor_id,
        )

    def create(
        self,
        *,
        organization_id: UUID,
        person_identity_id: UUID,
        representative_type: RepresentativeType,
        position: str | None,
        valid_from: datetime | None,
        source_document_reference: str | None,
        actor_id: str,
    ) -> LegalRepresentative:
        self._lock_organization(organization_id)
        if representative_type == "PRIMARY" and self._active_primary_model(organization_id) is not None:
            self.session.rollback()
            raise PrimaryRepresentativeConflictError

        model = self._new_model(
            organization_id=organization_id,
            person_identity_id=person_identity_id,
            representative_type=representative_type,
            position=position,
            valid_from=valid_from,
            source_document_reference=source_document_reference,
            actor_id=actor_id,
        )
        self.session.add(model)
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(model)
        return self._to_domain(model)

    def update(
        self, representative_id: UUID, *, expected_version: int, values: dict[str, Any], actor_id: str
    ) -> LegalRepresentative:
        model = load_for_update(
            self.session,
            Model,
            representative_id,
            expected_version=expected_version,
            not_found_message="La relación de representación no existe.",
        )
        if not model.is_active:
            self.session.rollback()
            raise InvalidStatusTransitionError("La relación está cerrada y es inmutable.")
        for field, value in values.items():
            setattr(model, field, value)
        model.updated_by = actor_id
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(model)
        return self._to_domain(model)

    def close(self, representative_id: UUID, *, expected_version: int, actor_id: str) -> LegalRepresentative:
        model = load_for_update(
            self.session,
            Model,
            representative_id,
            expected_version=expected_version,
            not_found_message="La relación de representación no existe.",
        )
        if not model.is_active:
            self.session.rollback()
            raise InvalidStatusTransitionError("La relación ya está cerrada; no se reactiva.")
        self._close_model(model, actor_id)
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(model)
        return self._to_domain(model)

    @staticmethod
    def _close_model(model: Model, actor_id: str) -> None:
        model.is_active = False
        model.valid_to = closing_instant(model.valid_from, datetime.now(timezone.utc))
        model.updated_by = actor_id

    def set_primary(
        self,
        organization_id: UUID,
        *,
        person_identity_id: UUID,
        position: str | None,
        valid_from: datetime | None,
        source_document_reference: str | None,
        current_primary_version: int | None,
        actor_id: str,
    ) -> tuple[LegalRepresentative, bool]:
        self._lock_organization(organization_id)
        current = self._active_primary_model(organization_id)

        if current is not None:
            if current_primary_version is None or current.version != current_primary_version:
                self.session.rollback()
                raise VersionConflictError
            if current.person_identity_id == person_identity_id:
                # Ya es el PRIMARY vigente: sin cambios (DS-04).
                self.session.rollback()
                return self._to_domain(current), False
            self._close_model(current, actor_id)
            flush_or_translate(self.session, duplicates=DUPLICATES)

        model = self._new_model(
            organization_id=organization_id,
            person_identity_id=person_identity_id,
            representative_type="PRIMARY",
            position=position,
            valid_from=valid_from,
            source_document_reference=source_document_reference,
            actor_id=actor_id,
        )
        self.session.add(model)
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(model)
        return self._to_domain(model), True

    @staticmethod
    def _to_domain(model: Model) -> LegalRepresentative:
        return LegalRepresentative(
            id=model.id,
            organization_identity_id=model.organization_identity_id,
            person_identity_id=model.person_identity_id,
            representative_type=model.representative_type,
            position=model.position,
            is_primary=model.is_primary,
            is_active=model.is_active,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            source_document_reference=model.source_document_reference,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
