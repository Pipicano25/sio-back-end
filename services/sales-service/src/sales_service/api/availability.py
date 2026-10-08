"""Disponibilidad de existencias de un borrador (`contracts/rest-api.md` ruta 9; Historia 4; R-08).

Lectura con membresía (sin asignación a la sucursal); consulta los saldos de Inventory con la
identidad técnica y no reserva.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from sio_auth import SIOAuth

from sales_service.api.dependencies import CompanyReader, ServicesDep
from sales_service.api.identity import SERVICE
from sales_service.api.openapi import READ_RESPONSES, TAG_SALES
from sales_service.api.schemas.sales import AvailabilityResponse


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_SALES])

    @router.get(
        "/companies/{company_id}/sales/{sale_id}/availability",
        response_model=AvailabilityResponse,
        summary="Existencias disponibles para las líneas de la venta (sin reservar)",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sales", "read")],
    )
    def sale_availability(company_id: CompanyReader, sale_id: UUID, services: ServicesDep) -> AvailabilityResponse:
        sale, rows = services.availability().availability(company_id, sale_id)
        return AvailabilityResponse.of(sale, rows)

    return router
