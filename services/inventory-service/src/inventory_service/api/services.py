"""Construcción por solicitud de los servicios de aplicación (inyección de dependencias)."""

from __future__ import annotations

from fastapi import Request

from inventory_service.api.dependencies import company_products, lock_timeout_ms, operational_context
from inventory_service.application.operation_service import OperationService
from inventory_service.application.reference_validation import ReferenceValidator
from inventory_service.application.reversal_service import ReversalService
from inventory_service.infrastructure.database import get_db_session
from inventory_service.infrastructure.repository import SqlInventoryRepository


def get_repository(request: Request):
    for session in get_db_session(request):
        yield SqlInventoryRepository(session, lock_timeout_ms=lock_timeout_ms(request))


def build_validator(request: Request) -> ReferenceValidator:
    return ReferenceValidator(operational_context(request), company_products(request))


def build_operation_service(request: Request, repository: SqlInventoryRepository) -> OperationService:
    return OperationService(repository, build_validator(request), audit_hook=getattr(request.app.state, "audit_hook", None))


def build_reversal_service(request: Request, repository: SqlInventoryRepository) -> ReversalService:
    return ReversalService(repository, build_validator(request), audit_hook=getattr(request.app.state, "audit_hook", None))
