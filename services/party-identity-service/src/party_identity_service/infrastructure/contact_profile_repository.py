"""Repositorio SQLAlchemy de perfiles de contacto versionados (FR-010–FR-022, R-03).

Un mismo repositorio sirve a personas y organizaciones (parametrizado por el
modelo de la versión y el del propietario). Las escrituras bloquean la fila del
propietario (`SELECT … FOR UPDATE`), lo que serializa reemplazos y cierres por
identidad; el índice único parcial `uq_*_active` es la defensa final.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, select, update
from sqlalchemy.orm import Session

from party_identity_service.application.exceptions import (
    ContactProfileAlreadyClosedError,
    ContactProfileNotFoundError,
    NotFoundError,
    VersionConflictError,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.contact import ContactData, ContactProfile
from party_identity_service.infrastructure.models import (
    OrganizationContactProfileModel,
    OrganizationIdentityModel,
    PersonContactProfileModel,
    PersonIdentityModel,
)
from party_identity_service.infrastructure.persistence import commit_or_translate, flush_or_translate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SQLAlchemyContactProfileRepository:
    """Persistencia de perfiles de un tipo de parte."""

    def __init__(
        self,
        session: Session,
        *,
        profile_model: type,
        owner_model: type,
        owner_column: str,
    ) -> None:
        self.session = session
        self.profile_model = profile_model
        self.owner_model = owner_model
        self.owner_column = owner_column
        self.active_constraint = f"uq_{profile_model.__tablename__}_active"

    # -- lecturas -------------------------------------------------------------

    def _owner_attr(self):
        return getattr(self.profile_model, self.owner_column)

    def get_active(self, owner_id: UUID) -> ContactProfile | None:
        model = self.session.scalars(
            select(self.profile_model).where(
                self._owner_attr() == owner_id,
                self.profile_model.is_active.is_(True),
            )
        ).first()
        return self._to_domain(model) if model is not None else None

    def get_version(self, profile_id: UUID) -> ContactProfile | None:
        model = self.session.get(self.profile_model, profile_id)
        return self._to_domain(model) if model is not None else None

    def list_versions(self, owner_id: UUID, *, page: int, page_size: int) -> PageResult[ContactProfile]:
        condition = self._owner_attr() == owner_id
        total = self.session.scalar(
            select(func.count()).select_from(self.profile_model).where(condition)
        ) or 0
        models = self.session.scalars(
            select(self.profile_model)
            .where(condition)
            .order_by(self.profile_model.valid_from.desc(), self.profile_model.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return PageResult(
            items=[self._to_domain(model) for model in models],
            page=page,
            page_size=page_size,
            total_records=total,
        )

    def has_history(self, owner_id: UUID) -> bool:
        return bool(
            self.session.scalar(
                select(exists().where(self._owner_attr() == owner_id))
            )
        )

    # -- escrituras -------------------------------------------------------------

    def _lock_owner(self, owner_id: UUID) -> None:
        owner = self.session.get(
            self.owner_model,
            owner_id,
            with_for_update=True,
            populate_existing=True,
        )
        if owner is None:
            self.session.rollback()
            raise NotFoundError("La identidad solicitada no existe.")

    def _active_model(self, owner_id: UUID):
        return self.session.scalars(
            select(self.profile_model)
            .where(self._owner_attr() == owner_id, self.profile_model.is_active.is_(True))
            .execution_options(populate_existing=True)
        ).first()

    def replace(
        self,
        owner_id: UUID,
        *,
        expected_active_id: UUID | None,
        expected_version: int | None,
        data: ContactData,
        confirmed_by_company_id: UUID,
        confirmed_by_user_id: UUID,
        actor_id: str,
    ) -> ContactProfile:
        self._lock_owner(owner_id)
        current = self._active_model(owner_id)

        # Revalidación tras las llamadas externas (R-03).
        if expected_active_id is None:
            if current is not None:
                self.session.rollback()
                raise VersionConflictError
        elif current is None or current.id != expected_active_id or current.version != expected_version:
            self.session.rollback()
            raise VersionConflictError

        now = _utcnow()

        if current is not None:
            current.is_active = False
            current.valid_to = now
            current.updated_by = actor_id
            flush_or_translate(self.session, duplicates={self.active_constraint: VersionConflictError})

        # `version` crece de forma monótona por propietario: una versión nueva
        # nunca reutiliza un número ya visto por los clientes, así una vista
        # desactualizada siempre se detecta (RC-03, R-03).
        next_version = (
            self.session.scalar(
                select(func.max(self.profile_model.version)).where(self._owner_attr() == owner_id)
            )
            or 0
        ) + 1

        values: dict[str, Any] = {
            self.owner_column: owner_id,
            "email": data.email,
            "phone": data.phone,
            "address_line": data.address_line,
            "country_id": data.country_id,
            "administrative_division_id": data.administrative_division_id,
            "city_id": data.city_id,
            "postal_code": data.postal_code,
            "is_active": True,
            "valid_from": now,
            "valid_to": None,
            "confirmed_by_company_id": confirmed_by_company_id,
            "confirmed_by_user_id": confirmed_by_user_id,
            "created_by": actor_id,
            "updated_by": actor_id,
        }
        model = self.profile_model(**values)
        self.session.add(model)
        flush_or_translate(self.session, duplicates={self.active_constraint: VersionConflictError})
        # El contador de concurrencia del ORM inicia cada fila en 1; se fija aquí
        # el número monótono por propietario en la misma transacción.
        self.session.execute(
            update(self.profile_model.__table__)
            .where(self.profile_model.__table__.c.id == model.id)
            .values(version=next_version)
        )
        commit_or_translate(self.session, duplicates={self.active_constraint: VersionConflictError})
        self.session.refresh(model)
        return self._to_domain(model)

    def close(self, owner_id: UUID, *, expected_version: int, actor_id: str) -> ContactProfile:
        self._lock_owner(owner_id)
        current = self._active_model(owner_id)

        if current is None:
            has_history = self.has_history(owner_id)
            self.session.rollback()
            if has_history:
                raise ContactProfileAlreadyClosedError
            raise ContactProfileNotFoundError(
                "La identidad nunca ha tenido un perfil de contacto."
            )

        if current.version != expected_version:
            self.session.rollback()
            raise VersionConflictError

        current.is_active = False
        current.valid_to = _utcnow()
        current.updated_by = actor_id
        commit_or_translate(self.session, duplicates={})
        self.session.refresh(current)
        return self._to_domain(current)

    def _to_domain(self, model) -> ContactProfile:
        return ContactProfile(
            id=model.id,
            owner_id=getattr(model, self.owner_column),
            email=model.email,
            phone=model.phone,
            address_line=model.address_line,
            country_id=model.country_id,
            administrative_division_id=model.administrative_division_id,
            city_id=model.city_id,
            postal_code=model.postal_code,
            is_active=model.is_active,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            confirmed_by_user_id=model.confirmed_by_user_id,
            confirmed_by_company_id=model.confirmed_by_company_id,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


def person_contact_profile_repository(session: Session) -> SQLAlchemyContactProfileRepository:
    return SQLAlchemyContactProfileRepository(
        session,
        profile_model=PersonContactProfileModel,
        owner_model=PersonIdentityModel,
        owner_column="person_identity_id",
    )


def organization_contact_profile_repository(session: Session) -> SQLAlchemyContactProfileRepository:
    return SQLAlchemyContactProfileRepository(
        session,
        profile_model=OrganizationContactProfileModel,
        owner_model=OrganizationIdentityModel,
        owner_column="organization_identity_id",
    )
