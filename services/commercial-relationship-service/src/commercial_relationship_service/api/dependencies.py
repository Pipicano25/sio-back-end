"""Dependencias FastAPI compartidas por los routers funcionales.

Las fábricas de puertos se fijan en `create_app`: en producción son siempre los
adaptadores HTTP reales; las pruebas inyectan dobles (FR-050). Cada fábrica
recibe la solicitud para propagar el token del usuario cuando corresponde.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request
from sio_auth import CurrentClaims
from sqlalchemy.orm import Session

from commercial_relationship_service.application.company_customer_service import (
    CompanyCustomerService,
)
from commercial_relationship_service.application.company_product_service import (
    CompanyProductService,
)
from commercial_relationship_service.application.company_scope import (
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.company_supplier_service import (
    CompanySupplierService,
)
from commercial_relationship_service.application.ports import (
    CompanyAccessDirectory,
    CompanyDirectory,
    PartyDirectory,
    ProductCatalogDirectory,
)
from commercial_relationship_service.infrastructure.database import get_db_session
from commercial_relationship_service.infrastructure.repositories import (
    CompanyCustomerRepository,
    CompanyProductRepository,
    CompanySupplierRepository,
)

AccessDirectoryFactory = Callable[[Request], CompanyAccessDirectory]
CompanyDirectoryFactory = Callable[[Request], CompanyDirectory]
ProductDirectoryFactory = Callable[[Request], ProductCatalogDirectory]
PartyDirectoryFactory = Callable[[Request], PartyDirectory]


def get_identity(claims: CurrentClaims) -> RequestIdentity:
    """Identidad de la solicitud con la exención técnica de R-11 ya evaluada."""
    return RequestIdentity.build(
        subject=claims.subject,
        grants=claims.permissions,
        raw_claims=claims.raw,
    )


def get_scope_service(request: Request) -> CompanyScopeService:
    return CompanyScopeService(request.app.state.access_directory_factory(request))


def _lazy(factory, request: Request):
    return lambda: factory(request)


def get_product_repository(session: Session = Depends(get_db_session)) -> CompanyProductRepository:
    return CompanyProductRepository(session)


def get_customer_repository(session: Session = Depends(get_db_session)) -> CompanyCustomerRepository:
    return CompanyCustomerRepository(session)


def get_supplier_repository(session: Session = Depends(get_db_session)) -> CompanySupplierRepository:
    return CompanySupplierRepository(session)


def get_product_service(
    request: Request,
    repository: CompanyProductRepository = Depends(get_product_repository),
) -> CompanyProductService:
    return CompanyProductService(
        repository, _lazy(request.app.state.product_directory_factory, request)
    )


def get_customer_service(
    request: Request,
    repository: CompanyCustomerRepository = Depends(get_customer_repository),
) -> CompanyCustomerService:
    return CompanyCustomerService(
        repository,
        _lazy(request.app.state.party_directory_factory, request),
        _lazy(request.app.state.company_directory_factory, request),
    )


def get_supplier_service(
    request: Request,
    repository: CompanySupplierRepository = Depends(get_supplier_repository),
) -> CompanySupplierService:
    return CompanySupplierService(
        repository,
        _lazy(request.app.state.party_directory_factory, request),
        _lazy(request.app.state.company_directory_factory, request),
    )
