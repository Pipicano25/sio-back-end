"""Router de unidades de medida (`contracts/rest-api.md` §1)."""

from fastapi import APIRouter, Depends, Query
from sio_auth import SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.schemas.catalog_base import (
    MeasurementType,
    UnitOfMeasureCreate,
    UnitOfMeasureResponse,
    UnitOfMeasureUpdate,
)
from product_catalog_service.api.schemas.catalog_query import BatchLookupRequest, UnitLookupResponse
from product_catalog_service.api.security import permission
from product_catalog_service.api.simple_catalog_router import build_simple_catalog_router
from product_catalog_service.application.catalog_query_service import CatalogQueryService
from product_catalog_service.infrastructure.database import get_db_session
from product_catalog_service.application.unit_of_measure_service import UnitOfMeasureService
from product_catalog_service.infrastructure.models import GlobalUnitOfMeasureModel

RESOURCE = "units-of-measure"


def _measurement_type_filter(
    measurement_type: MeasurementType | None = Query(default=None),
):
    if measurement_type is None:
        return None
    return lambda statement: statement.where(
        GlobalUnitOfMeasureModel.measurement_type == measurement_type
    )


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de unidades de medida."""
    router = APIRouter(prefix="/units-of-measure", tags=["Unidades de medida"])

    @router.post(
        "/batch-lookup",
        response_model=UnitLookupResponse,
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Consultar hasta 100 unidades por identificador",
    )
    def batch_lookup(body: BatchLookupRequest, session: Session = Depends(get_db_session)):
        return UnitLookupResponse(items=CatalogQueryService(session).lookup_units(body.ids))
    return build_simple_catalog_router(
        auth=auth,
        prefix="/units-of-measure",
        resource=RESOURCE,
        tag="Unidades de medida",
        service_class=UnitOfMeasureService,
        create_schema=UnitOfMeasureCreate,
        update_schema=UnitOfMeasureUpdate,
        response_schema=UnitOfMeasureResponse,
        extra_filters=_measurement_type_filter,
        router=router,
    )
