"""Adaptador de las agregaciones de Sales (SAL-R1 y SAL-R2) con el token del usuario (DR-07)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from business_reporting_service.application.ports import (
    BranchSales,
    PresentationSales,
    ProductSales,
    ProductSalesResult,
    SalesTotal,
)
from business_reporting_service.infrastructure.http_client import UserCaller
from business_reporting_service.infrastructure.parsing import (
    UnexpectedBody,
    decimal_of,
    int_of,
    items,
    text_of,
    uuid_of,
)


def _params(date_from: date, date_to: date, branch_ids: list[UUID]) -> list[tuple[str, str]]:
    return [("date_from", date_from.isoformat()), ("date_to", date_to.isoformat())] + [
        ("branch_id", str(branch)) for branch in branch_ids
    ]


class HTTPSales:
    def __init__(self, caller: UserCaller) -> None:
        self._caller = caller

    async def by_product(self, company_id: UUID, *, date_from: date, date_to: date, branch_ids: list[UUID],
                         order_by: str, limit: int, include_presentations: bool) -> ProductSalesResult:
        operation = "sales_by_product"
        params = _params(date_from, date_to, branch_ids) + [
            ("order_by", order_by), ("limit", str(limit)), ("include_presentations", str(include_presentations).lower())
        ]
        body = await self._caller.json(operation, "GET", f"/companies/{company_id}/sales-aggregates/by-product",
                                       params=params)
        try:
            products = [
                ProductSales(
                    company_product_id=uuid_of(item, "company_product_id"),
                    product_code=text_of(item, "product_code"),
                    product_name=text_of(item, "product_name"),
                    currency_code=text_of(item, "currency_code"),
                    quantity_base=decimal_of(item, "quantity_base"),
                    amount=decimal_of(item, "amount"),
                    sales_count=int_of(item, "sales_count"),
                    presentations=None if item.get("presentations") is None else [
                        PresentationSales(
                            uuid_of(p, "company_product_presentation_id", optional=True),
                            text_of(p, "code", optional=True), text_of(p, "name", optional=True),
                            decimal_of(p, "quantity"), decimal_of(p, "quantity_base"), decimal_of(p, "amount"),
                        )
                        for p in items(item, "presentations")
                    ],
                )
                for item in items(body)
            ]
            totals = [
                SalesTotal(text_of(t, "currency_code"), decimal_of(t, "amount"), int_of(t, "sales_count"))
                for t in items(body, "totals")
            ]
        except UnexpectedBody:
            raise self._caller.client.unavailable(operation, "cuerpo_inesperado") from None
        return ProductSalesResult(products, totals)

    async def by_branch(self, company_id: UUID, *, date_from: date, date_to: date,
                        branch_ids: list[UUID]) -> list[BranchSales]:
        operation = "sales_by_branch"
        body = await self._caller.json(operation, "GET", f"/companies/{company_id}/sales-aggregates/by-branch",
                                       params=_params(date_from, date_to, branch_ids))
        try:
            return [
                BranchSales(uuid_of(item, "branch_id"), text_of(item, "currency_code"), int_of(item, "sales_count"),
                            decimal_of(item, "total_amount"))
                for item in items(body)
            ]
        except UnexpectedBody:
            raise self._caller.client.unavailable(operation, "cuerpo_inesperado") from None
