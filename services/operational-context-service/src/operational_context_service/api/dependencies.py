"""Dependencias FastAPI compartidas por los routers funcionales.

Las fábricas de puertos se fijan en `create_app`: en producción son siempre los
adaptadores HTTP reales; las pruebas inyectan dobles (R-12).
"""

from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from operational_context_service.application.branch_service import BranchService
from operational_context_service.application.company_service import CompanyService
from operational_context_service.application.ports import (
    GeographyDirectory,
    OrganizationDirectory,
)
from operational_context_service.infrastructure.branch_repository import (
    SQLAlchemyBranchRepository,
)
from operational_context_service.infrastructure.company_repository import (
    SQLAlchemyCompanyRepository,
)
from operational_context_service.infrastructure.database import get_db_session

OrganizationDirectoryFactory = Callable[[Request], OrganizationDirectory]
GeographyDirectoryFactory = Callable[[Request], GeographyDirectory]


def get_organization_directory(request: Request) -> OrganizationDirectory:
    factory: OrganizationDirectoryFactory = request.app.state.organization_directory_factory
    return factory(request)


def get_geography_directory(request: Request) -> GeographyDirectory:
    factory: GeographyDirectoryFactory = request.app.state.geography_directory_factory
    return factory(request)


def get_company_service(
    session: Session = Depends(get_db_session),
    organizations: OrganizationDirectory = Depends(get_organization_directory),
    geography: GeographyDirectory = Depends(get_geography_directory),
) -> CompanyService:
    """Servicio de empresas para la solicitud actual."""
    return CompanyService(SQLAlchemyCompanyRepository(session), organizations, geography)


def get_branch_service(
    session: Session = Depends(get_db_session),
    geography: GeographyDirectory = Depends(get_geography_directory),
) -> BranchService:
    """Servicio de sucursales para la solicitud actual."""
    return BranchService(
        SQLAlchemyBranchRepository(session),
        SQLAlchemyCompanyRepository(session),
        geography,
    )
