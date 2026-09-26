"""Repositorio SQLAlchemy para identidades globales de personas."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from party_identity_service.application.exceptions import (
    DuplicateIdentificationError,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.person_identity import (
    IdentityStatus,
    PersonIdentificationType,
    PersonIdentity,
    PersonVerificationStatus,
)
from party_identity_service.infrastructure.models import (
    PersonIdentityModel,
)
from party_identity_service.infrastructure.persistence import (
    commit_or_translate,
    load_for_update,
)

DUPLICATE_CONSTRAINT = "uq_person_identities_identification"


class SQLAlchemyPersonIdentityRepository:
    """Implementa persistencia de personas mediante SQLAlchemy."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        """Inicializa el repositorio.

        Args:
            session: Sesión SQLAlchemy activa.
        """
        self.session = session

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        identification_country_id: UUID | None = None,
        identification_type: PersonIdentificationType | None = None,
        verification_status: PersonVerificationStatus | None = None,
        status: IdentityStatus = "ACTIVE",
    ) -> PageResult[PersonIdentity]:
        """Obtiene personas paginadas; por defecto solo `ACTIVE` (DS-02)."""
        conditions = [
            PersonIdentityModel.status == status,
        ]

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    PersonIdentityModel.identification_number.ilike(pattern),
                    PersonIdentityModel.first_name.ilike(pattern),
                    PersonIdentityModel.middle_name.ilike(pattern),
                    PersonIdentityModel.last_name.ilike(pattern),
                    PersonIdentityModel.second_last_name.ilike(pattern),
                )
            )

        if identification_country_id is not None:
            conditions.append(
                PersonIdentityModel.identification_country_id
                == identification_country_id
            )

        if identification_type is not None:
            conditions.append(
                PersonIdentityModel.identification_type
                == identification_type
            )

        if verification_status is not None:
            conditions.append(
                PersonIdentityModel.verification_status
                == verification_status
            )

        total_records = self.session.scalar(
            select(func.count())
            .select_from(PersonIdentityModel)
            .where(*conditions)
        ) or 0

        statement = (
            select(PersonIdentityModel)
            .where(*conditions)
            .order_by(
                PersonIdentityModel.last_name,
                PersonIdentityModel.first_name,
                PersonIdentityModel.id,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        models = self.session.scalars(
            statement,
        ).all()

        return PageResult(
            items=[
                self._to_domain(model)
                for model in models
            ],
            page=page,
            page_size=page_size,
            total_records=total_records,
        )

    def get_by_id(
        self,
        person_identity_id: UUID,
    ) -> PersonIdentity | None:
        """Obtiene una identidad de persona por identificador."""
        model = self.session.get(
            PersonIdentityModel,
            person_identity_id,
        )

        if model is None:
            return None

        return self._to_domain(model)

    def create(
        self,
        *,
        identification_country_id: UUID,
        identification_type: PersonIdentificationType,
        identification_number: str,
        first_name: str,
        middle_name: str | None,
        last_name: str,
        second_last_name: str | None,
        birth_date: date | None,
        verification_status: PersonVerificationStatus,
        actor_id: str,
    ) -> PersonIdentity:
        """Crea una identidad global de persona."""
        model = PersonIdentityModel(
            identification_country_id=identification_country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            second_last_name=second_last_name,
            birth_date=birth_date,
            verification_status=verification_status,
            status="ACTIVE",
            created_by=actor_id,
            updated_by=actor_id,
        )

        self.session.add(model)
        commit_or_translate(
            self.session,
            duplicates={DUPLICATE_CONSTRAINT: DuplicateIdentificationError},
        )
        self.session.refresh(model)

        return self._to_domain(model)

    def update(
        self,
        person_identity_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> PersonIdentity:
        """Modifica los campos indicados con control de versión."""
        model = load_for_update(
            self.session,
            PersonIdentityModel,
            person_identity_id,
            expected_version=expected_version,
            not_found_message="La persona solicitada no existe.",
        )

        for field, value in values.items():
            setattr(model, field, value)

        model.updated_by = actor_id
        commit_or_translate(
            self.session,
            duplicates={DUPLICATE_CONSTRAINT: DuplicateIdentificationError},
        )
        self.session.refresh(model)

        return self._to_domain(model)

    def set_status(
        self,
        person_identity_id: UUID,
        *,
        expected_version: int,
        status: IdentityStatus,
        actor_id: str,
    ) -> PersonIdentity:
        """Cambia el estado de uso con control de versión."""
        return self.update(
            person_identity_id,
            expected_version=expected_version,
            values={"status": status},
            actor_id=actor_id,
        )

    @staticmethod
    def _to_domain(
        model: PersonIdentityModel,
    ) -> PersonIdentity:
        """Convierte un modelo SQLAlchemy en entidad de dominio."""
        return PersonIdentity(
            id=model.id,
            identification_country_id=model.identification_country_id,
            identification_type=model.identification_type,
            identification_number=model.identification_number,
            first_name=model.first_name,
            middle_name=model.middle_name,
            last_name=model.last_name,
            second_last_name=model.second_last_name,
            birth_date=model.birth_date,
            verification_status=model.verification_status,
            status=model.status,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
