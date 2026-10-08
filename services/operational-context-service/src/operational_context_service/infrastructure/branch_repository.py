"""Repositorio SQLAlchemy de sucursales.

Las lecturas hacen `JOIN` con `companies` para devolver `company_status` y
`effective_timezone = coalesce(branches.timezone, companies.timezone)`,
calculados en la consulta y nunca persistidos (R-10, DS-08).

El alta y la reactivación leen la empresa con `SELECT ... FOR SHARE` dentro de
la transacción de escritura: una inactivación concurrente de la empresa
(`FOR UPDATE`) espera o hace esperar, y nunca queda una sucursal creada o
reactivada bajo una empresa inactiva (R-09, RN-09).
"""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from operational_context_service.application import audit_events as audit
from operational_context_service.application.exceptions import (
    CompanyInactiveError,
    DuplicateBranchCodeError,
    InvalidStatusTransitionError,
    NotFoundError,
)
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.ports import BranchFilters
from operational_context_service.domain.entities import Branch
from operational_context_service.infrastructure.models import BranchModel, CompanyModel
from operational_context_service.infrastructure.persistence import (
    commit_or_translate,
    load_for_update,
)

DUPLICATE_CODE = "uq_branches_company_id_code"
NOT_FOUND_MESSAGE = "La sucursal solicitada no existe."
COMPANY_NOT_FOUND_MESSAGE = "La empresa solicitada no existe."


def _branch_query() -> Select:
    return select(
        BranchModel,
        CompanyModel.status.label("company_status"),
        func.coalesce(BranchModel.timezone, CompanyModel.timezone).label("effective_timezone"),
    ).join(CompanyModel, CompanyModel.id == BranchModel.company_id)


class SQLAlchemyBranchRepository:
    """Persistencia de sucursales."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def end_read(self) -> None:
        """Cierra la transacción de lectura (R-09)."""
        if self.session.in_transaction():
            self.session.rollback()

    def get_by_id(self, branch_id: UUID) -> Branch | None:
        row = self.session.execute(
            _branch_query()
            .where(BranchModel.id == branch_id)
            .execution_options(populate_existing=True)
        ).one_or_none()

        return None if row is None else to_branch(*row)

    def exists_code(
        self,
        company_id: UUID,
        code: str,
        *,
        exclude_branch_id: UUID | None = None,
    ) -> bool:
        statement = select(BranchModel.id).where(
            BranchModel.company_id == company_id,
            BranchModel.code == code,
        )

        if exclude_branch_id is not None:
            statement = statement.where(BranchModel.id != exclude_branch_id)

        return self.session.scalar(statement.limit(1)) is not None

    def list_by_company(
        self,
        company_id: UUID,
        filters: BranchFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[Branch]:
        conditions = [
            BranchModel.company_id == company_id,
            BranchModel.status == filters.status,
        ]

        if filters.city_id is not None:
            conditions.append(BranchModel.city_id == filters.city_id)

        if filters.search:
            pattern = f"%{filters.search}%"
            conditions.append(
                or_(BranchModel.code.ilike(pattern), BranchModel.name.ilike(pattern)),
            )

        total_records = self.session.scalar(
            select(func.count()).select_from(BranchModel).where(*conditions)
        ) or 0

        rows = self.session.execute(
            _branch_query()
            .where(*conditions)
            .order_by(BranchModel.created_at, BranchModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return PageResult(
            items=[to_branch(*row) for row in rows],
            page=page,
            page_size=page_size,
            total_records=total_records,
        )

    def create_in_active_company(
        self,
        company_id: UUID,
        values: dict[str, Any],
        *,
        actor_id: str,
    ) -> Branch:
        """Inserta la sucursal si la empresa sigue `ACTIVE` (bloqueo `FOR SHARE`).

        Raises:
            NotFoundError: Si la empresa no existe.
            CompanyInactiveError: Si la empresa está inactiva.
            DuplicateBranchCodeError: Si el código ya existe en la empresa.
        """
        self._lock_active_company(company_id)
        branch_id = uuid4()
        model = BranchModel(
            id=branch_id,
            company_id=company_id,
            **values,
            status="ACTIVE",
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.session.add(model)
        audit.track_create(
            self.session, model, action=audit.CREATE_BRANCH, entity_type="Branch",
            company_id=company_id, branch_id=branch_id,
        )
        self._commit()

        return self._reload(branch_id)

    def update(
        self,
        branch_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> Branch:
        model = load_for_update(
            self.session,
            BranchModel,
            branch_id,
            expected_version=expected_version,
            not_found_message=NOT_FOUND_MESSAGE,
        )

        for field, value in values.items():
            setattr(model, field, value)

        model.updated_by = actor_id
        audit.track_update(
            self.session, model, action=audit.status_action(model, "BRANCH"), entity_type="Branch",
            company_id=model.company_id, branch_id=branch_id,
        )
        self._commit()

        return self._reload(branch_id)

    def reactivate_in_active_company(
        self,
        branch_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> Branch:
        """Reactiva la sucursal si su empresa sigue `ACTIVE` (bloqueo `FOR SHARE`)."""
        model = load_for_update(
            self.session,
            BranchModel,
            branch_id,
            expected_version=expected_version,
            not_found_message=NOT_FOUND_MESSAGE,
        )

        if model.status == "ACTIVE":
            self.session.rollback()
            raise InvalidStatusTransitionError("La sucursal ya se encuentra en estado ACTIVE.")

        self._lock_active_company(model.company_id)
        model.status = "ACTIVE"
        model.updated_by = actor_id
        audit.track_update(
            self.session, model, action=audit.REACTIVATE_BRANCH, entity_type="Branch",
            company_id=model.company_id, branch_id=branch_id,
        )
        self._commit()

        return self._reload(branch_id)

    def _lock_active_company(self, company_id: UUID) -> None:
        company = self.session.execute(
            select(CompanyModel.status)
            .where(CompanyModel.id == company_id)
            .with_for_update(read=True)
        ).scalar_one_or_none()

        if company is None:
            self.session.rollback()
            raise NotFoundError(COMPANY_NOT_FOUND_MESSAGE)

        if company != "ACTIVE":
            self.session.rollback()
            raise CompanyInactiveError

    def _commit(self) -> None:
        """Confirma la transacción; las pruebas de concurrencia lo sobrescriben
        para retener la transacción abierta en un punto controlado."""
        commit_or_translate(
            self.session,
            duplicates={DUPLICATE_CODE: DuplicateBranchCodeError},
        )

    def _reload(self, branch_id: UUID) -> Branch:
        branch = self.get_by_id(branch_id)
        self.end_read()

        if branch is None:  # pragma: no cover - la fila acaba de confirmarse
            raise NotFoundError(NOT_FOUND_MESSAGE)

        return branch


def to_branch(model: BranchModel, company_status: str, effective_timezone: str) -> Branch:
    """Convierte la fila (modelo + campos calculados) en entidad de dominio."""
    return Branch(
        id=model.id,
        company_id=model.company_id,
        company_status=company_status,
        code=model.code,
        name=model.name,
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
        effective_timezone=effective_timezone,
        status=model.status,
        version=model.version,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
