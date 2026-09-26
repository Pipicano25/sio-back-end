"""Lecturas de membresía por `sub` para el alcance y el acceso operativo (R-01).

Una consulta indexada por `(keycloak_user_id, status)` por solicitud; sin caché
entre solicitudes (FR-044).
"""

from uuid import UUID

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from operational_context_service.application.ports import MembershipRef
from operational_context_service.infrastructure.models import ApplicationUserModel


class SQLAlchemyMembershipLookup:
    """Implementación SQLAlchemy de `MembershipLookup`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def active_company_ids(self, keycloak_user_id: str) -> frozenset[UUID]:
        company_ids = self.session.scalars(
            select(ApplicationUserModel.company_id).where(
                ApplicationUserModel.keycloak_user_id == keycloak_user_id,
                ApplicationUserModel.status == "ACTIVE",
            )
        ).all()
        self._end_read()

        return frozenset(company_ids)

    def find_membership(self, company_id: UUID, keycloak_user_id: str) -> MembershipRef | None:
        row = self.session.execute(
            select(
                ApplicationUserModel.id,
                ApplicationUserModel.company_id,
                ApplicationUserModel.status,
            )
            .where(
                ApplicationUserModel.company_id == company_id,
                ApplicationUserModel.keycloak_user_id == keycloak_user_id,
            )
            .order_by(
                case((ApplicationUserModel.status == "ACTIVE", 0), else_=1),
                ApplicationUserModel.updated_at.desc(),
                ApplicationUserModel.id,
            )
            .limit(1)
        ).one_or_none()
        self._end_read()

        return None if row is None else MembershipRef(id=row.id, company_id=row.company_id, status=row.status)

    def _end_read(self) -> None:
        if self.session.in_transaction():
            self.session.rollback()
