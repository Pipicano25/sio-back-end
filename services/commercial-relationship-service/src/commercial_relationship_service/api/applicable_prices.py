"""Precio aplicable por lotes (`contracts/rest-api.md` §6 de la 010, contrato Provider; FR-055)."""

from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends
from sio_auth import SIOAuth

from commercial_relationship_service.api.company_scope import company_dependency
from commercial_relationship_service.api.dependencies import get_applicable_price_service
from commercial_relationship_service.api.openapi import TAG_APPLICABLE_PRICES
from commercial_relationship_service.api.schemas.price_list_item import (
    ApplicablePriceItem,
    ApplicablePriceRequest,
    ApplicablePriceResponse,
)
from commercial_relationship_service.application.applicable_price_service import (
    ApplicablePriceService,
    PriceLine,
)
from commercial_relationship_service.application.company_scope import SERVICE

RESOURCE = "price_list_items"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router del precio aplicable."""
    router = APIRouter(tags=[TAG_APPLICABLE_PRICES])

    @router.post(
        "/companies/{company_id}/applicable-prices/resolve",
        response_model=ApplicablePriceResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Resolver el precio aplicable de hasta 100 líneas (Provider)",
    )
    def resolve(
        body: ApplicablePriceRequest,
        company_id: UUID = Depends(company_dependency(write=False, lookup=True)),
        service: ApplicablePriceService = Depends(get_applicable_price_service),
    ):
        at, results = service.resolve(
            company_id,
            [
                PriceLine(
                    company_product_id=line.company_product_id,
                    company_product_presentation_id=line.company_product_presentation_id,
                    price_list_id=line.price_list_id,
                    line_id=line.line_id,
                )
                for line in body.lines
            ],
            at=body.at,
        )
        return ApplicablePriceResponse(
            at=at, items=[ApplicablePriceItem(**asdict(result)) for result in results]
        )

    return router
