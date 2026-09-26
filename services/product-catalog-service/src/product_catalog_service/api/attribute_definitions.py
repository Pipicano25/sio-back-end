"""Router de definiciones de atributo y opciones (`contracts/rest-api.md` §5)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.schemas.attribute import (
    AttributeDefinitionCreate,
    AttributeDefinitionResponse,
    AttributeDefinitionUpdate,
    DataType,
    OptionCreate,
    OptionResponse,
    OptionUpdate,
)
from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.security import permission
from product_catalog_service.api.simple_catalog_router import build_simple_catalog_router
from product_catalog_service.application.attribute_definition_service import (
    AttributeDefinitionService,
)
from product_catalog_service.infrastructure.database import get_db_session
from product_catalog_service.infrastructure.models import ProductAttributeDefinitionModel

RESOURCE = "attribute-definitions"


def _data_type_filter(data_type: DataType | None = Query(default=None)):
    if data_type is None:
        return None
    return lambda statement: statement.where(ProductAttributeDefinitionModel.data_type == data_type)


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de definiciones de atributo."""
    router = APIRouter(prefix="/attribute-definitions", tags=["Atributos"])

    def get_service(session: Session = Depends(get_db_session)) -> AttributeDefinitionService:
        return AttributeDefinitionService(session)

    options_path = "/{definition_id}/options"

    @router.get(
        options_path,
        response_model=list[OptionResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar las opciones de una definición",
    )
    def list_options(
        definition_id: UUID,
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        service: AttributeDefinitionService = Depends(get_service),
    ):
        return [OptionResponse.model_validate(item) for item in service.list_options(definition_id, status_filter)]

    @router.post(
        options_path,
        response_model=OptionResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Crear una opción (solo definiciones OPTION activas)",
    )
    def create_option(
        definition_id: UUID,
        body: OptionCreate,
        response: Response,
        actor: CurrentSubject,
        service: AttributeDefinitionService = Depends(get_service),
    ):
        option = service.create_option(definition_id, actor=actor, **body.model_dump())
        response.headers["Location"] = f"/api/v1/attribute-definitions/{definition_id}/options/{option.id}"
        return OptionResponse.model_validate(option)

    @router.put(
        options_path + "/{option_id}",
        response_model=OptionResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Modificar una opción",
    )
    def update_option(
        definition_id: UUID,
        option_id: UUID,
        body: OptionUpdate,
        actor: CurrentSubject,
        service: AttributeDefinitionService = Depends(get_service),
    ):
        return OptionResponse.model_validate(
            service.update_option(definition_id, option_id, actor=actor, **body.model_dump())
        )

    @router.post(
        options_path + "/{option_id}/deactivate",
        response_model=OptionResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Inactivar una opción",
    )
    def deactivate_option(
        definition_id: UUID,
        option_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: AttributeDefinitionService = Depends(get_service),
    ):
        return OptionResponse.model_validate(
            service.deactivate_option(definition_id, option_id, version=body.version, actor=actor)
        )

    @router.post(
        options_path + "/{option_id}/reactivate",
        response_model=OptionResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Reactivar una opción",
    )
    def reactivate_option(
        definition_id: UUID,
        option_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: AttributeDefinitionService = Depends(get_service),
    ):
        return OptionResponse.model_validate(
            service.reactivate_option(definition_id, option_id, version=body.version, actor=actor)
        )

    return build_simple_catalog_router(
        auth=auth,
        prefix="/attribute-definitions",
        resource=RESOURCE,
        tag="Atributos",
        service_class=AttributeDefinitionService,
        create_schema=AttributeDefinitionCreate,
        update_schema=AttributeDefinitionUpdate,
        response_schema=AttributeDefinitionResponse,
        extra_filters=_data_type_filter,
        router=router,
    )
