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
from party_identity_service.application.ports import (
    CountryDirectory,
    LocationDirectory,
    MembershipResolver,
)
from party_identity_service.application.contact_profile_service import (
    ContactProfileService,
)
from party_identity_service.infrastructure.contact_profile_repository import (
    organization_contact_profile_repository,
    person_contact_profile_repository,
)
from party_identity_service.application.contact_person_service import ContactPersonService
from party_identity_service.infrastructure.contact_person_repository import (
    SQLAlchemyContactPersonRepository,
)
from party_identity_service.application.business_sector_service import (
    BusinessSectorService,
    OrganizationBusinessSectorService,
)
from party_identity_service.infrastructure.business_sector_repository import (
    SQLAlchemyBusinessSectorRepository,
)
from party_identity_service.infrastructure.organization_business_sector_repository import (
    SQLAlchemyOrganizationBusinessSectorRepository,
)
from party_identity_service.application.legal_representative_service import (
    LegalRepresentativeService,
)
from party_identity_service.infrastructure.legal_representative_repository import (
    SQLAlchemyLegalRepresentativeRepository,
)
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
LocationDirectoryFactory = Callable[[Request], LocationDirectory]


def get_location_directory(request: Request) -> LocationDirectory:
    """Puerto de país, división y ciudad para la solicitud actual (Fase B)."""
    factory: LocationDirectoryFactory = request.app.state.location_directory_factory

    return factory(request)


def get_membership_resolver(request: Request) -> MembershipResolver:
    """Puerto hacia Operational Context (instancia única con su token en caché)."""
    return request.app.state.membership_resolver


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


# --------------------------------------------------------------------------
# Fase B
# --------------------------------------------------------------------------


def get_person_contact_profile_service(
    session: Session = Depends(get_db_session),
    locations: LocationDirectory = Depends(get_location_directory),
    memberships: MembershipResolver = Depends(get_membership_resolver),
) -> ContactProfileService:
    """Servicio de perfiles de contacto de personas."""
    return ContactProfileService(
        kind="person",
        profiles=person_contact_profile_repository(session),
        owners=SQLAlchemyPersonIdentityRepository(session),
        locations=locations,
        memberships=memberships,
    )


def get_organization_contact_profile_service(
    session: Session = Depends(get_db_session),
    locations: LocationDirectory = Depends(get_location_directory),
    memberships: MembershipResolver = Depends(get_membership_resolver),
) -> ContactProfileService:
    """Servicio de perfiles de contacto de organizaciones."""
    return ContactProfileService(
        kind="organization",
        profiles=organization_contact_profile_repository(session),
        owners=SQLAlchemyOrganizationIdentityRepository(session),
        locations=locations,
        memberships=memberships,
    )


def get_contact_person_service(
    session: Session = Depends(get_db_session),
) -> ContactPersonService:
    """Servicio de personas de contacto."""
    return ContactPersonService(
        contacts=SQLAlchemyContactPersonRepository(session),
        organizations=SQLAlchemyOrganizationIdentityRepository(session),
        persons=SQLAlchemyPersonIdentityRepository(session),
    )


def get_business_sector_service(
    session: Session = Depends(get_db_session),
) -> BusinessSectorService:
    """Servicio del catálogo de sectores."""
    return BusinessSectorService(sectors=SQLAlchemyBusinessSectorRepository(session))


def get_organization_business_sector_service(
    session: Session = Depends(get_db_session),
) -> OrganizationBusinessSectorService:
    """Servicio de sectores de organización."""
    return OrganizationBusinessSectorService(
        assignments=SQLAlchemyOrganizationBusinessSectorRepository(session),
        sectors=SQLAlchemyBusinessSectorRepository(session),
        organizations=SQLAlchemyOrganizationIdentityRepository(session),
    )


def get_legal_representative_service(
    session: Session = Depends(get_db_session),
) -> LegalRepresentativeService:
    """Servicio de representantes legales."""
    return LegalRepresentativeService(
        representatives=SQLAlchemyLegalRepresentativeRepository(session),
        organizations=SQLAlchemyOrganizationIdentityRepository(session),
        persons=SQLAlchemyPersonIdentityRepository(session),
    )
