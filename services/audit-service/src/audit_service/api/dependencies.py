"""Dependencias FastAPI de Audit Service (sesión, repositorio y puertos)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from audit_service.application.ports import CompanyAccessDirectory
from audit_service.application.query_service import QueryService
from audit_service.application.registration_service import RegistrationService
from audit_service.infrastructure.database import get_db_session
from audit_service.infrastructure.repository import SqlAlchemyAuditEventRepository

AccessDirectoryFactory = Callable[[Request], CompanyAccessDirectory]

DbSession = Annotated[Session, Depends(get_db_session)]


def get_registration_service(request: Request, session: DbSession) -> RegistrationService:
    return RegistrationService(
        SqlAlchemyAuditEventRepository(session),
        max_clock_skew_seconds=request.app.state.settings.max_clock_skew_seconds,
    )


def get_query_service(request: Request, session: DbSession) -> QueryService:
    factory: AccessDirectoryFactory = request.app.state.access_directory_factory
    return QueryService(
        SqlAlchemyAuditEventRepository(session),
        access_directory=lambda: factory(request),
    )
