"""Dependencias FastAPI compartidas por los routers funcionales.

Las fábricas de puertos se fijan en `create_app`: en producción son siempre los
adaptadores HTTP reales; las pruebas inyectan dobles (R-12).
"""

from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from operational_context_service.application.advisor_assignment_service import (
    AdvisorAssignmentService,
)
from operational_context_service.application.application_user_service import (
    ApplicationUserService,
)
from operational_context_service.application.branch_service import BranchService
from operational_context_service.application.company_service import CompanyService
from operational_context_service.application.operational_access_service import (
    OperationalAccessService,
)
from operational_context_service.application.user_branch_service import UserBranchService
from operational_context_service.application.ports import (
    GeographyDirectory,
    IdentityAccountDirectory,
    OrganizationDirectory,
    PersonDirectory,
)
from operational_context_service.infrastructure.advisor_assignment_repository import (
    SQLAlchemyAdvisorAssignmentRepository,
)
from operational_context_service.infrastructure.application_user_repository import (
    SQLAlchemyApplicationUserRepository,
)
from operational_context_service.infrastructure.branch_repository import (
    SQLAlchemyBranchRepository,
)
from operational_context_service.infrastructure.company_repository import (
    SQLAlchemyCompanyRepository,
)
from operational_context_service.infrastructure.database import get_db_session
from operational_context_service.infrastructure.membership_lookup import SQLAlchemyMembershipLookup
from operational_context_service.infrastructure.user_branch_repository import (
    SQLAlchemyUserBranchRepository,
)

OrganizationDirectoryFactory = Callable[[Request], OrganizationDirectory]
GeographyDirectoryFactory = Callable[[Request], GeographyDirectory]
PersonDirectoryFactory = Callable[[Request], PersonDirectory]
AccountDirectoryFactory = Callable[[Request], IdentityAccountDirectory]


def get_person_directory(request: Request) -> PersonDirectory:
    factory: PersonDirectoryFactory = request.app.state.person_directory_factory
    return factory(request)


def get_account_directory(request: Request) -> IdentityAccountDirectory:
    factory: AccountDirectoryFactory = request.app.state.account_directory_factory
    return factory(request)


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


def get_application_user_service(
    session: Session = Depends(get_db_session),
    accounts: IdentityAccountDirectory = Depends(get_account_directory),
    persons: PersonDirectory = Depends(get_person_directory),
) -> ApplicationUserService:
    """Servicio de usuarios operativos para la solicitud actual (Fase B)."""
    return ApplicationUserService(
        SQLAlchemyApplicationUserRepository(session),
        SQLAlchemyCompanyRepository(session),
        accounts,
        persons,
    )


def get_user_branch_service(session: Session = Depends(get_db_session)) -> UserBranchService:
    """Servicio de asignaciones usuario–sucursal (Fase B; sin proveedores externos)."""
    return UserBranchService(
        SQLAlchemyUserBranchRepository(session),
        SQLAlchemyApplicationUserRepository(session),
        SQLAlchemyBranchRepository(session),
    )


def get_operational_access_service(
    session: Session = Depends(get_db_session),
    accounts: IdentityAccountDirectory = Depends(get_account_directory),
) -> OperationalAccessService:
    """Servicio de acceso operativo (Fase B). Keycloak solo para la vía técnica con permiso."""
    return OperationalAccessService(
        SQLAlchemyCompanyRepository(session),
        SQLAlchemyBranchRepository(session),
        SQLAlchemyUserBranchRepository(session),
        SQLAlchemyMembershipLookup(session),
        accounts,
        SQLAlchemyApplicationUserRepository(session),
    )


def get_advisor_assignment_service(
    session: Session = Depends(get_db_session),
    persons: PersonDirectory = Depends(get_person_directory),
) -> AdvisorAssignmentService:
    """Servicio de asesores (Fase B). Party Identity solo al asignar una persona."""
    return AdvisorAssignmentService(
        SQLAlchemyAdvisorAssignmentRepository(session),
        SQLAlchemyCompanyRepository(session),
        persons,
    )
