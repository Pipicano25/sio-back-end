"""Rutas de lectura de la spec 022: PC-1 (resumen por lotes) y PC-2 (productos por filtros).

`contracts/product-catalog.md` de la spec 022. Son lecturas por `POST` (cuerpos con listas de ids);
no escriben ni auditan. Exigen `perm:product-catalog:products:read`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sio_auth import SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.schemas.catalog_query import BatchLookupRequest
from product_catalog_service.api.schemas.product_summary import (
    MatchPosition,
    ProductMatchConductorResponse,
    ProductMatchEvaluatorResponse,
    ProductMatchItem,
    ProductMatchRequest,
    ProductSummaryResponse,
)
from product_catalog_service.api.security import permission
from product_catalog_service.application.product_summary_service import ProductSummaryService
from product_catalog_service.infrastructure.database import get_db_session

RESOURCE = "products"
_FILTER_FIELDS = ("brand_ids", "category_ids", "include_descendants", "identifier", "product_type", "status", "has_image")


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de PC-1 y PC-2."""
    router = APIRouter(prefix="/products", tags=["Productos"])

    def get_service(request: Request, session: Session = Depends(get_db_session)) -> ProductSummaryService:
        return ProductSummaryService(session, request.app.state.settings)

    @router.post(
        "/summaries/batch-lookup",
        response_model=ProductSummaryResponse,
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Resumen de hasta 100 productos globales (spec 022, PC-1)",
        description=(
            "Nombre canónico, tipo, estado, marca, unidad base, categorías e identificadores `ACTIVE`, y la imagen "
            "principal: `has_image` y `image_url` (URL absoluta y firmada de la ruta pública, o `null`). Un número "
            "fijo de consultas por lote. El `batch-lookup` existente no cambia."
        ),
    )
    def summaries(body: BatchLookupRequest, service: ProductSummaryService = Depends(get_service)):
        return ProductSummaryResponse(items=service.summaries(body.ids))

    @router.post(
        "/match",
        response_model=ProductMatchConductorResponse | ProductMatchEvaluatorResponse,
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Productos globales que cumplen filtros (spec 022, PC-2)",
        description=(
            "Con `candidate_ids` (hasta 100) devuelve los que cumplen los filtros, en el orden recibido. Sin ellos, "
            "recorre los productos en orden de nombre canónico normalizado e `id`, de a `limit` (1 a 100), después de "
            "`after`; cada elemento trae su `position`. Sin conteos: `has_more` indica si hay más."
        ),
    )
    def match(body: ProductMatchRequest, service: ProductSummaryService = Depends(get_service)):
        values = body.model_dump(include=set(_FILTER_FIELDS))
        if body.candidate_ids is not None:
            return ProductMatchEvaluatorResponse(ids=service.match_candidates(values, body.candidate_ids))
        after = (body.after.k[0], body.after.id) if body.after is not None else None
        rows, has_more = service.match_page(values, after=after, limit=body.limit)
        return ProductMatchConductorResponse(
            items=[ProductMatchItem(id=product_id, position=MatchPosition(k=[key], id=product_id)) for product_id, key in rows],
            has_more=has_more,
        )

    return router
