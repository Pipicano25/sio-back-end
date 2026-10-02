"""Repositorio SQLAlchemy de personas de contacto (FR-040–FR-047, R-05)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from party_identity_service.application.exceptions import (
    DuplicateActiveContactPersonError,
    InvalidPrimaryContactError,
    NotFoundError,
    PrimaryContactConflictError,
    VersionConflictError,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.contact import ContactPerson
from party_identity_service.infrastructure.models import (
    OrganizationContactPersonModel as Model,
    OrganizationIdentityModel,
)
from party_identity_service.infrastructure.persistence import (
    commit_or_translate,
    flush_or_translate,
    load_for_update,
)

DUPLICATES = {
    "uq_organization_contact_persons_primary": PrimaryContactConflictError,
    "uq_organization_contact_persons_person": DuplicateActiveContactPersonError,
}


class SQLAlchemyContactPersonRepository:
    """Persistencia de `organization_contact_persons`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_organization(
        self, organization_id: UUID, *, is_active: bool, page: int, page_size: int
    ) -> PageResult[ContactPerson]:
        conditions = [Model.organization_identity_id == organization_id, Model.is_active.is_(is_active)]
        total = self.session.scalar(select(func.count()).select_from(Model).where(*conditions)) or 0
        models = self.session.scalars(
            select(Model)
            .where(*conditions)
            .order_by(Model.is_primary.desc(), Model.created_at, Model.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return PageResult(
            items=[self._to_domain(model) for model in models],
            page=page,
            page_size=page_size,
            total_records=total,
        )

    def get_by_id(self, contact_id: UUID) -> ContactPerson | None:
        model = self.session.get(Model, contact_id)
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
        person_identity_id: UUID | None,
        position: str | None,
        email: str | None,
        phone: str | None,
        is_primary: bool,
        actor_id: str,
    ) -> ContactPerson:
        self._lock_organization(organization_id)
        if is_primary and self._current_primary(organization_id) is not None:
            self.session.rollback()
            raise PrimaryContactConflictError

        model = Model(
            organization_identity_id=organization_id,
            person_identity_id=person_identity_id,
            position=position,
            email=email,
            phone=phone,
            is_primary=is_primary,
            is_active=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.session.add(model)
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(model)
        return self._to_domain(model)

    def update(
        self, contact_id: UUID, *, expected_version: int, values: dict[str, Any], actor_id: str
    ) -> ContactPerson:
        model = load_for_update(
            self.session,
            Model,
            contact_id,
            expected_version=expected_version,
            not_found_message="La persona de contacto no existe.",
        )
        for field, value in values.items():
            setattr(model, field, value)
        model.updated_by = actor_id
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(model)
        return self._to_domain(model)

    def set_active(
        self, contact_id: UUID, *, expected_version: int, active: bool, actor_id: str
    ) -> ContactPerson:
        values: dict[str, Any] = {"is_active": active}
        if not active:
            # Inactivar quita la marca de principal solo de esta fila (DS-07).
            values["is_primary"] = False
        return self.update(contact_id, expected_version=expected_version, values=values, actor_id=actor_id)

    def set_primary(self, contact_id: UUID, *, expected_version: int, actor_id: str) -> ContactPerson:
        # Se obtiene la organización sin cargar la entidad, para no dejar en la sesión
        # una versión anterior al bloqueo.
        organization_id = self.session.scalar(
            select(Model.organization_identity_id).where(Model.id == contact_id)
        )
        if organization_id is None:
            raise NotFoundError("La persona de contacto no existe.")

        self._lock_organization(organization_id)
        target = self.session.get(Model, contact_id, with_for_update=True, populate_existing=True)

        if target.version != expected_version:
            self.session.rollback()
            raise VersionConflictError
        if not target.is_active:
            self.session.rollback()
            raise InvalidPrimaryContactError
        if target.is_primary:
            # Ya es el principal: sin cambios (DS-04).
            self.session.rollback()
            return self._to_domain(target)

        previous = self._current_primary(organization_id, exclude=contact_id)
        if previous is not None:
            previous.is_primary = False
            previous.updated_by = actor_id
            flush_or_translate(self.session, duplicates=DUPLICATES)

        target.is_primary = True
        target.updated_by = actor_id
        commit_or_translate(self.session, duplicates=DUPLICATES)
        self.session.refresh(target)
        return self._to_domain(target)

    @staticmethod
    def _to_domain(model: Model) -> ContactPerson:
        return ContactPerson(
            id=model.id,
            organization_identity_id=model.organization_identity_id,
            person_identity_id=model.person_identity_id,
            position=model.position,
            email=model.email,
            phone=model.phone,
            is_primary=model.is_primary,
            is_active=model.is_active,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
