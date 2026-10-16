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
from commercial_relationship_service.application.company_product_tax_service import CompanyProductTaxService
from commercial_relationship_service.application.company_scope import (
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.applicable_price_service import (
    ApplicablePriceService,
)
from commercial_relationship_service.application.company_product_presentation_service import (
    CompanyProductPresentationService,
)
from commercial_relationship_service.application.company_supplier_service import (
    CompanySupplierService,
)
from commercial_relationship_service.application.ports import (
    CompanyAccessDirectory,
    CompanyDirectory,
    PartyDirectory,
    PaymentReferenceDirectory,
    ProductCatalogDirectory,
)
from commercial_relationship_service.application.price_list_item_service import (
    PriceListItemService,
)
from commercial_relationship_service.application.price_list_service import PriceListService
from commercial_relationship_service.application.pricing_policy_service import PricingPolicyService
from commercial_relationship_service.application.automatic_price_application_service import (
    AutomaticPriceResolutionService,
)
from commercial_relationship_service.application.automatic_price_request_service import AutomaticPriceRequestService
from commercial_relationship_service.application.supplier_payment_condition_service import (
    SupplierPaymentConditionService,
)
from commercial_relationship_service.application.supplier_product_service import (
    SupplierProductService,
)
from commercial_relationship_service.infrastructure.database import get_db_session
from commercial_relationship_service.infrastructure.pricing_repositories import (
    AutomaticPriceApplicationRepository,
    AutomaticPricingRepository,
    PricingPolicyRepository,
)
from commercial_relationship_service.infrastructure.repositories import (
    CompanyCustomerRepository,
    CompanyProductPresentationRepository,
    CompanyProductRepository,
    CompanySupplierRepository,
    PriceListItemRepository,
    PriceListRepository,
    SupplierPaymentConditionRepository,
    SupplierProductRepository,
)

AccessDirectoryFactory = Callable[[Request], CompanyAccessDirectory]
CompanyDirectoryFactory = Callable[[Request], CompanyDirectory]
ProductDirectoryFactory = Callable[[Request], ProductCatalogDirectory]
PartyDirectoryFactory = Callable[[Request], PartyDirectory]
PaymentDirectoryFactory = Callable[[Request], PaymentReferenceDirectory]


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


# --------------------------------------------------------------------------
# Fase B (specs/010-commercial-relationship-commercial-product)
# --------------------------------------------------------------------------
# Los repositorios de una misma solicitud comparten la sesión: así el bloqueo del
# ámbito y la escritura ocurren en la misma transacción (R-04).


def get_presentation_repository(
    session: Session = Depends(get_db_session),
) -> CompanyProductPresentationRepository:
    return CompanyProductPresentationRepository(session)


def get_supplier_product_repository(
    session: Session = Depends(get_db_session),
) -> SupplierProductRepository:
    return SupplierProductRepository(session)


def get_payment_condition_repository(
    session: Session = Depends(get_db_session),
) -> SupplierPaymentConditionRepository:
    return SupplierPaymentConditionRepository(session)


def get_price_list_repository(session: Session = Depends(get_db_session)) -> PriceListRepository:
    return PriceListRepository(session)


def get_price_list_item_repository(
    session: Session = Depends(get_db_session),
) -> PriceListItemRepository:
    return PriceListItemRepository(session)


def get_presentation_service(
    request: Request,
    session: Session = Depends(get_db_session),
) -> CompanyProductPresentationService:
    return CompanyProductPresentationService(
        CompanyProductPresentationRepository(session),
        CompanyProductRepository(session),
        _lazy(request.app.state.product_directory_factory, request),
    )


def get_supplier_product_service(
    request: Request,
    session: Session = Depends(get_db_session),
) -> SupplierProductService:
    return SupplierProductService(
        SupplierProductRepository(session),
        CompanyProductRepository(session),
        CompanySupplierRepository(session),
        CompanyProductPresentationRepository(session),
        _lazy(request.app.state.product_directory_factory, request),
    )


def get_payment_condition_service(
    request: Request,
    session: Session = Depends(get_db_session),
) -> SupplierPaymentConditionService:
    return SupplierPaymentConditionService(
        SupplierPaymentConditionRepository(session),
        CompanySupplierRepository(session),
        _lazy(request.app.state.payment_directory_factory, request),
    )


def get_price_list_service(session: Session = Depends(get_db_session)) -> PriceListService:
    return PriceListService(PriceListRepository(session))


def get_price_list_item_service(session: Session = Depends(get_db_session)) -> PriceListItemService:
    return PriceListItemService(
        PriceListItemRepository(session),
        PriceListRepository(session),
        CompanyProductRepository(session),
        CompanyProductPresentationRepository(session),
    )


def get_applicable_price_service(session: Session = Depends(get_db_session)) -> ApplicablePriceService:
    return ApplicablePriceService(PriceListItemRepository(session))


def get_pricing_policy_repository(session: Session = Depends(get_db_session)) -> PricingPolicyRepository:
    return PricingPolicyRepository(session)


def get_pricing_policy_service(session: Session = Depends(get_db_session)) -> PricingPolicyService:
    return PricingPolicyService(
        PricingPolicyRepository(session),
        PriceListRepository(session),
        CompanyProductPresentationRepository(session),
    )


def get_product_tax_service(session: Session = Depends(get_db_session)) -> CompanyProductTaxService:
    return CompanyProductTaxService(CompanyProductRepository(session))


def get_automatic_price_request_service(session: Session = Depends(get_db_session)) -> AutomaticPriceRequestService:
    return AutomaticPriceRequestService(AutomaticPricingRepository(session), CompanyProductPresentationRepository(session))


def get_automatic_price_application_repository(
    session: Session = Depends(get_db_session),
) -> AutomaticPriceApplicationRepository:
    return AutomaticPriceApplicationRepository(session)


def get_automatic_price_resolution_service(session: Session = Depends(get_db_session)) -> AutomaticPriceResolutionService:
    return AutomaticPriceResolutionService(AutomaticPriceApplicationRepository(session))
