"""Dependencias FastAPI compartidas por los routers funcionales."""

from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from party_identity_service.application.identification_type_rule_service import (
    IdentificationTypeRuleService,
)
from party_identity_service.application.organization_identity_service import (
    OrganizationIdentityService,
)
from party_identity_service.application.person_identity_service import (
    PersonIdentityService,
)
from party_identity_service.application.ports import CountryDirectory
from party_identity_service.infrastructure.database import get_db_session
from party_identity_service.infrastructure.identification_type_rule_repository import (
    SQLAlchemyIdentificationTypeRuleRepository,
)
from party_identity_service.infrastructure.organization_identity_repository import (
    SQLAlchemyOrganizationIdentityRepository,
)
from party_identity_service.infrastructure.person_identity_repository import (
    SQLAlchemyPersonIdentityRepository,
)

CountryDirectoryFactory = Callable[[Request], CountryDirectory]


def get_country_directory(request: Request) -> CountryDirectory:
    """Construye el puerto de Geography para la solicitud actual.

    La fábrica se fija en `create_app`: en producción es siempre el adaptador
    HTTP; las pruebas inyectan un doble (FR-044).
    """
    factory: CountryDirectoryFactory = request.app.state.country_directory_factory

    return factory(request)


def get_person_identity_service(
    session: Session = Depends(get_db_session),
    country_directory: CountryDirectory = Depends(get_country_directory),
) -> PersonIdentityService:
    """Construye el servicio de aplicación de personas."""
    return PersonIdentityService(
        SQLAlchemyPersonIdentityRepository(session),
        SQLAlchemyIdentificationTypeRuleRepository(session),
        country_directory,
    )


def get_organization_identity_service(
    session: Session = Depends(get_db_session),
    country_directory: CountryDirectory = Depends(get_country_directory),
) -> OrganizationIdentityService:
    """Construye el servicio de aplicación de organizaciones."""
    return OrganizationIdentityService(
        SQLAlchemyOrganizationIdentityRepository(session),
        SQLAlchemyIdentificationTypeRuleRepository(session),
        country_directory,
    )


def get_identification_type_rule_service(
    session: Session = Depends(get_db_session),
    country_directory: CountryDirectory = Depends(get_country_directory),
) -> IdentificationTypeRuleService:
    """Construye el servicio de aplicación de reglas."""
    return IdentificationTypeRuleService(
        SQLAlchemyIdentificationTypeRuleRepository(session),
        country_directory,
    )
