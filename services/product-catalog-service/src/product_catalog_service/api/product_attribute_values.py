"""Router de valores de atributo del producto (`contracts/rest-api.md` §6.3)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.schemas.attribute_value import AttributeValuePut
from product_catalog_service.api.schemas.dependents import AttributeValueResponse
from product_catalog_service.api.security import permission
from product_catalog_service.application.attribute_value_service import (
    AttributeValueService,
    ValueView,
)
from product_catalog_service.infrastructure.database import get_db_session

RESOURCE = "products"


def _view(item: ValueView) -> AttributeValueResponse:
    response = AttributeValueResponse.model_validate(item.value)
    response.out_of_classification = item.out_of_classification
    return response


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de valores de atributo."""
    router = APIRouter(prefix="/products/{product_id}/attribute-values", tags=["Productos: atributos"])

    def get_service(session: Session = Depends(get_db_session)) -> AttributeValueService:
        return AttributeValueService(session)

    @router.get(
        "",
        response_model=list[AttributeValueResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar los valores de atributo del producto",
    )
    def list_values(product_id: UUID, service: AttributeValueService = Depends(get_service)):
        return [_view(item) for item in service.list(product_id)]

    @router.put(
        "/{definition_id}",
        response_model=AttributeValueResponse,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Registrar o reemplazar el valor de un atributo",
        responses={201: {"description": "Valor creado"}},
    )
    def put_value(
        product_id: UUID,
        definition_id: UUID,
        body: AttributeValuePut,
        response: Response,
        actor: CurrentSubject,
        service: AttributeValueService = Depends(get_service),
    ):
        payload = body.model_dump(exclude={"version"})
        view, created = service.set_value(
            product_id,
            definition_id,
            payload=payload,
            version=body.version,
            actor=actor,
        )
        response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return _view(view)

    @router.delete(
        "/{definition_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[permission(auth, RESOURCE, "delete")],
        summary="Retirar el valor (eliminación física, DS-08)",
    )
    def delete_value(
        product_id: UUID,
        definition_id: UUID,
        version: int = Query(ge=1),
        service: AttributeValueService = Depends(get_service),
    ):
        service.remove_value(product_id, definition_id, version=version)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
