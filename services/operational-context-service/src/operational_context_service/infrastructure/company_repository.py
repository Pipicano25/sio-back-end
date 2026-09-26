"""Repositorio SQLAlchemy de empresas."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from operational_context_service.application.exceptions import (
    DuplicateOrganizationIdentityError,
)
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.ports import CompanyFilters
from operational_context_service.domain.entities import Company
from operational_context_service.infrastructure.models import CompanyModel
from operational_context_service.infrastructure.persistence import (
    commit_or_translate,
    load_for_update,
)

DUPLICATE_ORGANIZATION = "uq_companies_organization_identity_id"
NOT_FOUND_MESSAGE = "La empresa solicitada no existe."


class SQLAlchemyCompanyRepository:
    """Persistencia de empresas."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def end_read(self) -> None:
        """Cierra la transacción de lectura para no mantenerla abierta durante
        llamadas HTTP a otros servicios (R-09)."""
        if self.session.in_transaction():
            self.session.rollback()

    def get_by_id(self, company_id: UUID) -> Company | None:
        model = self.session.get(CompanyModel, company_id, populate_existing=True)

        return None if model is None else to_company(model)

    def exists_organization(
        self,
        organization_identity_id: UUID,
        *,
        exclude_company_id: UUID | None = None,
    ) -> bool:
        statement = select(CompanyModel.id).where(
            CompanyModel.organization_identity_id == organization_identity_id,
        )

        if exclude_company_id is not None:
            statement = statement.where(CompanyModel.id != exclude_company_id)

        return self.session.scalar(statement.limit(1)) is not None

    def list_all(
        self,
        filters: CompanyFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[Company]:
        conditions = [CompanyModel.status == filters.status]

        if filters.organization_identity_id is not None:
            conditions.append(
                CompanyModel.organization_identity_id == filters.organization_identity_id,
            )

        if filters.country_id is not None:
            conditions.append(CompanyModel.country_id == filters.country_id)

        if filters.city_id is not None:
            conditions.append(CompanyModel.city_id == filters.city_id)

        total_records = self.session.scalar(
            select(func.count()).select_from(CompanyModel).where(*conditions)
        ) or 0

        models = self.session.scalars(
            select(CompanyModel)
            .where(*conditions)
            .order_by(CompanyModel.created_at, CompanyModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return PageResult(
            items=[to_company(model) for model in models],
            page=page,
            page_size=page_size,
            total_records=total_records,
        )

    def create(self, values: dict[str, Any], *, actor_id: str) -> Company:
        model = CompanyModel(
            **values,
            status="ACTIVE",
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.session.add(model)
        self._commit()
        self.session.refresh(model)

        return to_company(model)

    def update(
        self,
        company_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> Company:
        """Modifica con `SELECT ... FOR UPDATE` y versión esperada.

        El bloqueo exclusivo de la fila espera a las transacciones que la
        tienen con `FOR SHARE` (alta o reactivación de sucursal, R-09).
        """
        model = load_for_update(
            self.session,
            CompanyModel,
            company_id,
            expected_version=expected_version,
            not_found_message=NOT_FOUND_MESSAGE,
        )

        for field, value in values.items():
            setattr(model, field, value)

        model.updated_by = actor_id
        self._commit()
        self.session.refresh(model)

        return to_company(model)

    def _commit(self) -> None:
        commit_or_translate(
            self.session,
            duplicates={DUPLICATE_ORGANIZATION: DuplicateOrganizationIdentityError},
        )


def to_company(model: CompanyModel) -> Company:
    """Convierte el modelo en entidad de dominio."""
    return Company(
        id=model.id,
        organization_identity_id=model.organization_identity_id,
        email=model.email,
        phone=model.phone,
        address_line=model.address_line,
        country_id=model.country_id,
        administrative_division_id=model.administrative_division_id,
        city_id=model.city_id,
        postal_code=model.postal_code,
        latitude=model.latitude,
        longitude=model.longitude,
        timezone=model.timezone,
        default_currency=model.default_currency,
        status=model.status,
        version=model.version,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
