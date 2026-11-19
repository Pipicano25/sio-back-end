"""Rutas de la adopción masiva (`specs/027-bulk-product-adoption/contracts/bulk-adoption.md`).

Historia 1: `POST /companies/{company_id}/bulk-adoptions` con `mode=PRESENTATIONS`. Exige los dos permisos de la
adopción individual (`company_products:create` **y** `company_product_presentations:create`) y la misma
membresía con la empresa `ACTIVE` que `company_products.py`. Las rutas de procesos en segundo plano
(`bulk-adoption-jobs`) llegan con la Historia 3.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import company_dependency
from commercial_relationship_service.api.dependencies import get_bulk_adoption_service
from commercial_relationship_service.api.schemas.bulk_adoption import (
    BulkAdoptionRequest,
    BulkAdoptionResponse,
    BulkPresentationResult,
    BulkProductResult,
)
from commercial_relationship_service.application.bulk_adoption_service import (
    BulkAdoptionService,
    PresentationRequest,
)
from commercial_relationship_service.application.company_scope import SERVICE

TAG = "Adopción masiva"
PRODUCTS_RESOURCE = "company_products"
PRESENTATIONS_RESOURCE = "company_product_presentations"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de la adopción masiva."""
    router = APIRouter(tags=[TAG])

    @router.post(
        "/companies/{company_id}/bulk-adoptions",
        response_model=BulkAdoptionResponse,
        dependencies=[
            auth.permission(SERVICE, PRODUCTS_RESOURCE, "create"),
            auth.permission(SERVICE, PRESENTATIONS_RESOURCE, "create"),
        ],
        summary="Adoptar en bloque una lista de presentaciones globales (spec 027)",
        description=(
            "Adopta de 1 a 100 presentaciones globales distintas (`mode=PRESENTATIONS`) y, por debajo, el producto "
            "de cada una cuando la empresa aún no lo tiene. Responde en espera con el resultado de cada producto y "
            "de cada presentación: `ADOPTED`, `ALREADY_ADOPTED` o `REJECTED` con su motivo. Cada adopción es la "
            "misma de las rutas individuales (validaciones, primer uso en Product Catalog y auditoría) y es "
            "independiente: un rechazo no revierte lo demás. Lo que no se envía se completa: nombre = nombre "
            "canónico, moneda `COP`, banderas por defecto y código interno = código de barras principal de la "
            "presentación base o el consecutivo `P-000001` de la empresa. `mode=PRODUCTS` aún no está disponible "
            "(`422`)."
        ),
    )
    def bulk_adopt(
        body: BulkAdoptionRequest,
        actor: CurrentSubject,
        company_id: UUID = Depends(company_dependency(write=True)),
        service: BulkAdoptionService = Depends(get_bulk_adoption_service),
    ):
        items = [
            PresentationRequest(
                global_product_presentation_id=item.global_product_presentation_id,
                product_values=item.product.sent() if item.product is not None else {},
                presentation_values=item.presentation.sent() if item.presentation is not None else {},
            )
            for item in body.items
        ]
        defaults = body.defaults.sent() if body.defaults is not None else {}
        result = service.adopt_presentations(company_id, items, defaults, actor=actor)

        return BulkAdoptionResponse(
            company_id=company_id,
            mode=body.mode,
            totals=result.totals(),
            products=[
                BulkProductResult(
                    global_product_id=item.global_product_id,
                    company_product_id=item.company_product_id,
                    internal_code=item.internal_code,
                    result=item.result,
                    reason=item.reason,
                )
                for item in result.products
            ],
            presentations=[
                BulkPresentationResult(
                    global_product_presentation_id=item.global_product_presentation_id,
                    global_product_id=item.global_product_id,
                    company_product_presentation_id=item.company_product_presentation_id,
                    result=item.result,
                    reason=item.reason,
                )
                for item in result.presentations
            ],
        )

    return router
