"""Adaptador de las compras del período de Purchase (PUR-R1) con el token del usuario (DR-07)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from business_reporting_service.application.ports import PurchasePage, PurchaseRow, PurchaseTotals
from business_reporting_service.infrastructure.http_client import UserCaller
from business_reporting_service.infrastructure.parsing import (
    UnexpectedBody,
    date_of,
    datetime_of,
    decimal_of,
    int_of,
    items,
    obj,
    text_of,
    uuid_of,
)


class HTTPPurchase:
    def __init__(self, caller: UserCaller) -> None:
        self._caller = caller

    async def period(self, company_id: UUID, *, date_from: date, date_to: date, branch_ids: list[UUID],
                     categories: list[str], page: int, page_size: int) -> PurchasePage:
        operation = "purchase_period"
        params = [("date_from", date_from.isoformat()), ("date_to", date_to.isoformat()), ("page", str(page)),
                  ("page_size", str(page_size))]
        params += [("branch_id", str(branch)) for branch in branch_ids] + [("category", c) for c in categories]
        body = await self._caller.json(operation, "GET", f"/companies/{company_id}/purchase-reports/period",
                                       params=params)
        try:
            rows = [
                PurchaseRow(
                    id=uuid_of(item, "id"), operation_date=date_of(item, "operation_date"),
                    received_at=datetime_of(item, "received_at", optional=True), branch_id=uuid_of(item, "branch_id"),
                    supplier_name=text_of(item, "supplier_name"),
                    supplier_identification=text_of(item, "supplier_identification"),
                    number=text_of(item, "number", optional=True),
                    supplier_document_number=text_of(item, "supplier_document_number", optional=True),
                    status=text_of(item, "status"), category=text_of(item, "category"),
                    receipt_status=text_of(item, "receipt_status", optional=True),
                    currency_code=text_of(item, "currency_code"), total=decimal_of(item, "total"),
                )
                for item in items(body)
            ]
            totals = [
                PurchaseTotals(
                    text_of(t, "currency_code"), int_of(t, "received_count"), decimal_of(t, "received_total"),
                    int_of(t, "pending_receipt_count"), decimal_of(t, "pending_receipt_total"),
                    int_of(t, "cancelled_count"), decimal_of(t, "cancelled_total"), decimal_of(t, "effective_total"),
                )
                for t in items(body, "totals")
            ]
            total_records = int_of(obj(body), "total_records")
        except UnexpectedBody:
            raise self._caller.client.unavailable(operation, "cuerpo_inesperado") from None
        return PurchasePage(rows, totals, total_records)
