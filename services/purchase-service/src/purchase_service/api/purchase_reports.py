"""Compras del período para reportes (spec 023, PUR-R1; solo lectura).

Mismas reglas que las lecturas de compras: usuario humano, `perm:purchase:purchases:read` y membresía `ACTIVE` en
la empresa (sin asignación a la sucursal, DS-09). No cambia ninguna ruta existente.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sio_auth import SIOAuth

from purchase_service.api.dependencies import CompanyReader, ServicesDep
from purchase_service.api.identity import SERVICE
from purchase_service.api.openapi import READ_RESPONSES, TAG_REPORTS
from purchase_service.api.schemas.purchase_reports import PeriodPage, PeriodPurchaseOut, PeriodQuery, PeriodTotalsOut
from purchase_service.api.schemas.purchases import MONEY, fmt, total_pages


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_REPORTS])

    @router.get(
        "/companies/{company_id}/purchase-reports/period",
        response_model=PeriodPage,
        summary="Compras del período, sin líneas, con totales por categoría (spec 023, PUR-R1)",
        description=(
            "Compras no `DRAFT` con `operation_date` entre `date_from` y `date_to` (incluidas; como máximo 366 días). "
            "`category`: `RECEIVED` (confirmada y recibida), `PENDING_RECEIPT` (confirmada sin recibir: no es "
            "mercancía recibida) o `CANCELLED` (anulada, aunque se hubiera recibido). `receipt_status` conserva su "
            "significado de la spec 020. `totals` es del período completo, por moneda: `effective_total` = "
            "recibidas + pendientes; las anuladas se informan y nunca suman. Orden `operation_date, number, id`. "
            "Permiso: `perm:purchase:purchases:read` y membresía en la empresa."
        ),
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchases", "read")],
    )
    def period(company_id: CompanyReader, query: Annotated[PeriodQuery, Query()], services: ServicesDep) -> PeriodPage:
        branch_ids = list(dict.fromkeys(query.branch_id))
        result = services.reports().period(
            company_id, date_from=query.date_from, date_to=query.date_to, branch_ids=branch_ids,
            categories=list(dict.fromkeys(query.category)), page=query.page, page_size=query.page_size,
        )
        return PeriodPage(
            company_id=company_id, date_from=query.date_from, date_to=query.date_to, branch_ids=branch_ids,
            items=[PeriodPurchaseOut.of(row) for row in result.items],
            totals=[
                PeriodTotalsOut(
                    currency_code=t.currency_code,
                    received_count=t.received_count, received_total=fmt(t.received_total, MONEY),
                    pending_receipt_count=t.pending_receipt_count,
                    pending_receipt_total=fmt(t.pending_receipt_total, MONEY),
                    cancelled_count=t.cancelled_count, cancelled_total=fmt(t.cancelled_total, MONEY),
                    effective_total=fmt(t.effective_total, MONEY),
                )
                for t in result.totals
            ],
            page=query.page, page_size=query.page_size, total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )

    return router
