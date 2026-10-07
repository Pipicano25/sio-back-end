"""Consultas de compras, líneas y operaciones (Historia 6; FR-039, FR-040).

La autorización (permiso de lectura y membresía `ACTIVE` en la empresa) la resuelve la
capa API antes de llegar aquí; todas las consultas filtran por `company_id` (RC-04).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from purchase_service.application.exceptions import NotFoundError
from purchase_service.application.purchase_service import PurchaseView
from purchase_service.infrastructure.models import PurchaseOperation
from purchase_service.infrastructure.repository import PurchaseRepository


@dataclass(frozen=True, slots=True)
class PurchasePage:
    items: list[PurchaseView]
    total_records: int


class QueryService:
    def __init__(self, repository: PurchaseRepository) -> None:
        self._repo = repository

    def purchase(self, company_id: UUID, purchase_id: UUID) -> PurchaseView:
        purchase = self._repo.get_purchase(company_id, purchase_id)
        if purchase is None:
            raise NotFoundError()
        pending = self._repo.pending_operation(purchase.id)
        return PurchaseView(purchase, self._repo.lines(purchase.id), pending.id if pending else None)

    def list(
        self,
        company_id: UUID,
        *,
        status: str | None,
        branch_id: UUID | None,
        supplier_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        number: str | None,
        page: int,
        page_size: int,
    ) -> PurchasePage:
        result = self._repo.list_purchases(
            company_id,
            status=status,
            branch_id=branch_id,
            supplier_id=supplier_id,
            date_from=date_from,
            date_to=date_to,
            number=number,
            page=page,
            page_size=page_size,
        )
        pending = self._repo.pending_operation_ids([purchase.id for purchase in result.items])
        return PurchasePage(
            [PurchaseView(purchase, [], pending.get(purchase.id)) for purchase in result.items], result.total_records
        )

    def operations(self, company_id: UUID, purchase_id: UUID) -> list[PurchaseOperation]:
        if self._repo.get_purchase(company_id, purchase_id) is None:
            raise NotFoundError()
        return self._repo.operations_of(purchase_id)

    def operation(self, company_id: UUID, operation_id: UUID) -> PurchaseOperation:
        operation = self._repo.get_operation(company_id, operation_id)
        if operation is None:
            raise NotFoundError()
        return operation
