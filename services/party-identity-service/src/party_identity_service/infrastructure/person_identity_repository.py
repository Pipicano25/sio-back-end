"""Repositorio SQLAlchemy para identidades globales de personas."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from party_identity_service.application.exceptions import (
    PersonIdentityConflictError,
    PersonIdentityVersionConflictError,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.person_identity import (
    PersonIdentificationType,
    PersonIdentity,
    PersonVerificationStatus,
)
from party_identity_service.infrastructure.models import (
    PersonIdentityModel,
)


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
    ) -> PageResult[PersonIdentity]:
        """Obtiene personas paginadas aplicando búsqueda y filtros."""
        conditions = []

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
        actor_uuid = UUID(actor_id)
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
            created_by=actor_uuid,
            updated_by=actor_uuid,
        )

        self.session.add(model)

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise PersonIdentityConflictError(
                "Ya existe una persona con el país, tipo y número "
                "de identificación indicados."
            ) from None

        self.session.refresh(model)

        return self._to_domain(model)

    def update(
        self,
        person_identity_id: UUID,
        *,
        expected_version: int,
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
    ) -> PersonIdentity | None:
        """Actualiza completamente una identidad global de persona."""
        model = self.session.get(
            PersonIdentityModel,
            person_identity_id,
        )

        if model is None:
            return None

        if model.version != expected_version:
            raise PersonIdentityVersionConflictError(
                "El registro fue modificado por otra operación. "
                "Consulte nuevamente antes de actualizar."
            )

        model.identification_country_id = identification_country_id
        model.identification_type = identification_type
        model.identification_number = identification_number
        model.first_name = first_name
        model.middle_name = middle_name
        model.last_name = last_name
        model.second_last_name = second_last_name
        model.birth_date = birth_date
        model.verification_status = verification_status
        model.updated_by = UUID(actor_id)

        try:
            self.session.commit()

        except IntegrityError:
            self.session.rollback()

            raise PersonIdentityConflictError(
                "Ya existe una persona con el país, tipo y número "
                "de identificación indicados."
            ) from None

        except StaleDataError:
            self.session.rollback()

            raise PersonIdentityVersionConflictError(
                "El registro fue modificado por otra operación. "
                "Consulte nuevamente antes de actualizar."
            ) from None

        self.session.refresh(model)

        return self._to_domain(model)

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
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
