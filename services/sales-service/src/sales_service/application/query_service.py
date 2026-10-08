"""Consultas de ventas, líneas y operaciones (Historia 6; FR-039, FR-040).

La autorización (permiso de lectura y membresía `ACTIVE` en la empresa) la resuelve la
capa API antes de llegar aquí; todas las consultas filtran por `company_id` (RC-04).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sales_service.application.exceptions import NotFoundError
from sales_service.application.sale_service import SaleView
from sales_service.infrastructure.models import SaleOperation
from sales_service.infrastructure.repository import SaleRepository


@dataclass(frozen=True, slots=True)
class SalePage:
    items: list[SaleView]
    total_records: int


class QueryService:
    def __init__(self, repository: SaleRepository) -> None:
        self._repo = repository

    def sale(self, company_id: UUID, sale_id: UUID) -> SaleView:
        sale = self._repo.get_sale(company_id, sale_id)
        if sale is None:
            raise NotFoundError()
        pending = self._repo.pending_operation(sale.id)
        return SaleView(sale, self._repo.lines(sale.id), pending.id if pending else None)

    def list(
        self,
        company_id: UUID,
        *,
        status: str | None,
        branch_id: UUID | None,
        customer_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        number: str | None,
        page: int,
        page_size: int,
    ) -> SalePage:
        result = self._repo.list_sales(
            company_id,
            status=status,
            branch_id=branch_id,
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
            number=number,
            page=page,
            page_size=page_size,
        )
        pending = self._repo.pending_operation_ids([sale.id for sale in result.items])
        return SalePage(
            [SaleView(sale, [], pending.get(sale.id)) for sale in result.items], result.total_records
        )

    def operations(self, company_id: UUID, sale_id: UUID) -> list[SaleOperation]:
        if self._repo.get_sale(company_id, sale_id) is None:
            raise NotFoundError()
        return self._repo.operations_of(sale_id)

    def operation(self, company_id: UUID, operation_id: UUID) -> SaleOperation:
        operation = self._repo.get_operation(company_id, operation_id)
        if operation is None:
            raise NotFoundError()
        return operation
