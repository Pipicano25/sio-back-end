"""Repositorio SQLAlchemy para identidades globales de organizaciones."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from party_identity_service.application.exceptions import (
    DuplicateIdentificationError,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.organization_identity import (
    OrganizationIdentificationType,
    OrganizationIdentity,
)
from party_identity_service.domain.person_identity import IdentityStatus
from party_identity_service.infrastructure.models import (
    OrganizationIdentityModel,
)
from party_identity_service.infrastructure.persistence import (
    commit_or_translate,
    load_for_update,
)

DUPLICATE_CONSTRAINT = "uq_organization_identities_identification"


class SQLAlchemyOrganizationIdentityRepository:
    """Implementa persistencia de organizaciones mediante SQLAlchemy."""

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
        country_id: UUID | None = None,
        identification_type: OrganizationIdentificationType | None = None,
        registration_status: str | None = None,
        status: IdentityStatus = "ACTIVE",
    ) -> PageResult[OrganizationIdentity]:
        """Obtiene organizaciones paginadas; por defecto solo `ACTIVE`."""
        conditions = [
            OrganizationIdentityModel.status == status,
        ]

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    OrganizationIdentityModel.identification_number.ilike(
                        pattern,
                    ),
                    OrganizationIdentityModel.legal_name.ilike(pattern),
                    OrganizationIdentityModel.trade_name.ilike(pattern),
                )
            )

        if country_id is not None:
            conditions.append(
                OrganizationIdentityModel.country_id == country_id,
            )

        if identification_type is not None:
            conditions.append(
                OrganizationIdentityModel.identification_type
                == identification_type,
            )

        if registration_status is not None:
            conditions.append(
                OrganizationIdentityModel.registration_status
                == registration_status,
            )

        total_records = self.session.scalar(
            select(func.count())
            .select_from(OrganizationIdentityModel)
            .where(*conditions)
        ) or 0

        statement = (
            select(OrganizationIdentityModel)
            .where(*conditions)
            .order_by(
                OrganizationIdentityModel.legal_name,
                OrganizationIdentityModel.id,
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
        organization_identity_id: UUID,
    ) -> OrganizationIdentity | None:
        """Obtiene una identidad de organización por identificador."""
        model = self.session.get(
            OrganizationIdentityModel,
            organization_identity_id,
        )

        if model is None:
            return None

        return self._to_domain(model)

    def create(
        self,
        *,
        country_id: UUID,
        identification_type: OrganizationIdentificationType,
        identification_number: str,
        legal_name: str,
        trade_name: str | None,
        organization_type: str | None,
        registration_status: str | None,
        website: str | None,
        actor_id: str,
    ) -> OrganizationIdentity:
        """Crea una identidad global de organización."""
        model = OrganizationIdentityModel(
            country_id=country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            legal_name=legal_name,
            trade_name=trade_name,
            organization_type=organization_type,
            registration_status=registration_status,
            website=website,
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
        organization_identity_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> OrganizationIdentity:
        """Modifica los campos indicados con control de versión."""
        model = load_for_update(
            self.session,
            OrganizationIdentityModel,
            organization_identity_id,
            expected_version=expected_version,
            not_found_message="La organización solicitada no existe.",
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
        organization_identity_id: UUID,
        *,
        expected_version: int,
        status: IdentityStatus,
        actor_id: str,
    ) -> OrganizationIdentity:
        """Cambia el estado de uso con control de versión."""
        return self.update(
            organization_identity_id,
            expected_version=expected_version,
            values={"status": status},
            actor_id=actor_id,
        )

    @staticmethod
    def _to_domain(
        model: OrganizationIdentityModel,
    ) -> OrganizationIdentity:
        """Convierte un modelo SQLAlchemy en entidad de dominio."""
        return OrganizationIdentity(
            id=model.id,
            country_id=model.country_id,
            identification_type=model.identification_type,
            identification_number=model.identification_number,
            legal_name=model.legal_name,
            trade_name=model.trade_name,
            organization_type=model.organization_type,
            registration_status=model.registration_status,
            website=model.website,
            status=model.status,
            version=model.version,
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
