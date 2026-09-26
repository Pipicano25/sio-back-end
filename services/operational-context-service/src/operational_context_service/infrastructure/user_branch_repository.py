"""Repositorio SQLAlchemy de asignaciones usuario–sucursal (Fase B).

Las lecturas calculan `membership_status`, `branch_status` y `company_status`
por JOIN (no se persisten). El alta y la reactivación bloquean con
`SELECT ... FOR SHARE` la membresía, la sucursal y la empresa y comprueban que
sigan `ACTIVE` dentro de la transacción de escritura (RN-10). La misma empresa
la garantizan además las FK compuestas (R-05, RC-06).
"""

from uuid import UUID, uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from operational_context_service.application.exceptions import (
    BranchCompanyMismatchError,
    BranchInactiveError,
    CompanyInactiveError,
    DuplicateUserBranchError,
    InvalidStatusTransitionError,
    MembershipInactiveError,
    NotFoundError,
)
from operational_context_service.application.pagination import PageResult
from operational_context_service.domain.entities import UserBranch
from operational_context_service.domain.status import EntityStatus
from operational_context_service.infrastructure.models import (
    ApplicationUserModel,
    BranchModel,
    CompanyModel,
    UserBranchModel,
)
from operational_context_service.infrastructure.persistence import (
    commit_or_translate,
    load_for_update,
)

DUPLICATE_PAIR = "uq_user_branches_application_user_id_branch_id"
FK_USER_COMPANY = "fk_user_branches_application_user_company"
FK_BRANCH_COMPANY = "fk_user_branches_branch_company"
NOT_FOUND_MESSAGE = "La asignación solicitada no existe."


def _query() -> Select:
    return (
        select(
            UserBranchModel,
            ApplicationUserModel.status.label("membership_status"),
            BranchModel.status.label("branch_status"),
            CompanyModel.status.label("company_status"),
        )
        .join(ApplicationUserModel, ApplicationUserModel.id == UserBranchModel.application_user_id)
        .join(BranchModel, BranchModel.id == UserBranchModel.branch_id)
        .join(CompanyModel, CompanyModel.id == UserBranchModel.company_id)
    )


class SQLAlchemyUserBranchRepository:
    """Persistencia de asignaciones usuario–sucursal."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def end_read(self) -> None:
        if self.session.in_transaction():
            self.session.rollback()

    def get_by_id(self, user_branch_id: UUID) -> UserBranch | None:
        row = self.session.execute(
            _query()
            .where(UserBranchModel.id == user_branch_id)
            .execution_options(populate_existing=True)
        ).one_or_none()

        return None if row is None else to_user_branch(*row)

    def find_pair(self, application_user_id: UUID, branch_id: UUID) -> UserBranch | None:
        row = self.session.execute(
            _query().where(
                UserBranchModel.application_user_id == application_user_id,
                UserBranchModel.branch_id == branch_id,
            )
        ).one_or_none()

        return None if row is None else to_user_branch(*row)

    def list_all_for_user(self, application_user_id: UUID) -> list[UserBranch]:
        """Todas las asignaciones (activas e inactivas) de una membresía."""
        rows = self.session.execute(
            _query()
            .where(UserBranchModel.application_user_id == application_user_id)
            .order_by(UserBranchModel.created_at, UserBranchModel.id)
        ).all()

        return [to_user_branch(*row) for row in rows]

    def list_by(
        self,
        *,
        application_user_id: UUID | None = None,
        branch_id: UUID | None = None,
        status: EntityStatus,
        page: int,
        page_size: int,
    ) -> PageResult[UserBranch]:
        conditions = [UserBranchModel.status == status]

        if application_user_id is not None:
            conditions.append(UserBranchModel.application_user_id == application_user_id)

        if branch_id is not None:
            conditions.append(UserBranchModel.branch_id == branch_id)

        total_records = self.session.scalar(
            select(func.count()).select_from(UserBranchModel).where(*conditions)
        ) or 0
        rows = self.session.execute(
            _query()
            .where(*conditions)
            .order_by(UserBranchModel.created_at, UserBranchModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return PageResult(
            items=[to_user_branch(*row) for row in rows],
            page=page,
            page_size=page_size,
            total_records=total_records,
        )

    def create(
        self,
        *,
        application_user_id: UUID,
        branch_id: UUID,
        company_id: UUID,
        actor_id: str,
    ) -> UserBranch:
        """Inserta la asignación si membresía, sucursal y empresa siguen `ACTIVE`."""
        self._lock_active_parents(application_user_id, branch_id, company_id)
        user_branch_id = uuid4()
        self.session.add(
            UserBranchModel(
                id=user_branch_id,
                application_user_id=application_user_id,
                branch_id=branch_id,
                company_id=company_id,
                status="ACTIVE",
                assigned_by=actor_id,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
        self._commit()

        return self._reload(user_branch_id)

    def deactivate(self, user_branch_id: UUID, *, expected_version: int, actor_id: str) -> UserBranch:
        model = self._load(user_branch_id, expected_version)

        if model.status == "INACTIVE":
            self.session.rollback()
            raise InvalidStatusTransitionError("La asignación ya se encuentra en estado INACTIVE.")

        model.status = "INACTIVE"
        # Hora de la base: misma fuente que `assigned_at` (server_default now()).
        model.deactivated_at = func.now()
        model.updated_by = actor_id
        self._commit()

        return self._reload(user_branch_id)

    def reactivate(self, user_branch_id: UUID, *, expected_version: int, actor_id: str) -> UserBranch:
        """Reactiva: borra `deactivated_at` y renueva fecha y autor de la asignación (FR-023)."""
        model = self._load(user_branch_id, expected_version)

        if model.status == "ACTIVE":
            self.session.rollback()
            raise InvalidStatusTransitionError("La asignación ya se encuentra en estado ACTIVE.")

        self._lock_active_parents(model.application_user_id, model.branch_id, model.company_id)
        model.status = "ACTIVE"
        model.deactivated_at = None
        model.assigned_at = func.now()
        model.assigned_by = actor_id
        model.updated_by = actor_id
        self._commit()

        return self._reload(user_branch_id)

    def _load(self, user_branch_id: UUID, expected_version: int) -> UserBranchModel:
        return load_for_update(
            self.session,
            UserBranchModel,
            user_branch_id,
            expected_version=expected_version,
            not_found_message=NOT_FOUND_MESSAGE,
        )

    def _lock_active_parents(self, application_user_id: UUID, branch_id: UUID, company_id: UUID) -> None:
        membership = self.session.execute(
            select(ApplicationUserModel.status)
            .where(ApplicationUserModel.id == application_user_id)
            .with_for_update(read=True)
        ).scalar_one_or_none()
        branch = self.session.execute(
            select(BranchModel.status)
            .where(BranchModel.id == branch_id)
            .with_for_update(read=True)
        ).scalar_one_or_none()
        company = self.session.execute(
            select(CompanyModel.status)
            .where(CompanyModel.id == company_id)
            .with_for_update(read=True)
        ).scalar_one_or_none()

        for status, error in (
            (membership, MembershipInactiveError(field="application_user_id")),
            (company, CompanyInactiveError(
                "La empresa está inactiva: no se pueden crear ni reactivar asignaciones.",
            )),
            (branch, BranchInactiveError(field="branch_id")),
        ):
            if status is None:
                self.session.rollback()
                raise NotFoundError("El recurso solicitado no existe.")

            if status != "ACTIVE":
                self.session.rollback()
                raise error

    def _commit(self) -> None:
        commit_or_translate(
            self.session,
            duplicates={
                DUPLICATE_PAIR: DuplicateUserBranchError(field="branch_id"),
                FK_USER_COMPANY: BranchCompanyMismatchError(field="branch_id"),
                FK_BRANCH_COMPANY: BranchCompanyMismatchError(field="branch_id"),
            },
        )

    def _reload(self, user_branch_id: UUID) -> UserBranch:
        user_branch = self.get_by_id(user_branch_id)
        self.end_read()

        if user_branch is None:  # pragma: no cover - la fila acaba de confirmarse
            raise NotFoundError(NOT_FOUND_MESSAGE)

        return user_branch


def to_user_branch(
    model: UserBranchModel,
    membership_status: str,
    branch_status: str,
    company_status: str,
) -> UserBranch:
    """Convierte la fila (modelo + estados calculados) en entidad de dominio."""
    return UserBranch(
        id=model.id,
        application_user_id=model.application_user_id,
        branch_id=model.branch_id,
        company_id=model.company_id,
        status=model.status,
        assigned_at=model.assigned_at,
        assigned_by=model.assigned_by,
        deactivated_at=model.deactivated_at,
        membership_status=membership_status,
        branch_status=branch_status,
        company_status=company_status,
        version=model.version,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
