"""Dependencias FastAPI de Inventory Service (sesión, servicios y puertos inyectados)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from inventory_service.application.ports import (
    CompanyAccessDirectory,
    CompanyProductDirectory,
    OperationalContextDirectory,
)
from inventory_service.infrastructure.database import get_db_session

OperationalContextFactory = Callable[[], OperationalContextDirectory]
CompanyProductFactory = Callable[[], CompanyProductDirectory]
AccessDirectoryFactory = Callable[[Request], CompanyAccessDirectory]

DbSession = Annotated[Session, Depends(get_db_session)]


def operational_context(request: Request) -> OperationalContextDirectory:
    factory: OperationalContextFactory = request.app.state.operational_context_factory
    return factory()


def company_products(request: Request) -> CompanyProductDirectory:
    factory: CompanyProductFactory = request.app.state.commercial_relationship_factory
    return factory()


def access_directory(request: Request) -> CompanyAccessDirectory:
    factory: AccessDirectoryFactory = request.app.state.access_directory_factory
    return factory(request)


def lock_timeout_ms(request: Request) -> int:
    return request.app.state.database.lock_timeout_ms
