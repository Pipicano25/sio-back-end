"""Consultas de saldo, stock, kardex y operaciones (FR-040 a FR-046).

El alcance (empresa autorizada) ya lo resolvió la capa API; aquí toda consulta
filtra por `company_id` (y `branch_id` cuando aplica) en SQL, de modo que nunca se
devuelven datos de otra empresa (RC-06).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from inventory_service.application.exceptions import NotFoundError
from inventory_service.infrastructure.repository import BalanceRow, Page, SqlInventoryRepository, StoredOperation


class QueryService:
    def __init__(self, repository: SqlInventoryRepository) -> None:
        self._repository = repository

    def balance(self, company_id: UUID, branch_id: UUID, product_id: UUID) -> BalanceRow | None:
        return self._repository.get_balance(company_id, branch_id, product_id)

    def balances(self, company_id: UUID, branch_id: UUID, product_ids: Sequence[UUID]) -> dict[UUID, BalanceRow]:
        return self._repository.get_balances(company_id, branch_id, product_ids)

    def stock(
        self, company_id: UUID, branch_id: UUID, *, product_id: UUID | None, in_stock_only: bool, page: int, page_size: int
    ) -> Page:
        return self._repository.list_balances(
            company_id, branch_id, product_id=product_id, in_stock_only=in_stock_only, page=page, page_size=page_size
        )

    def kardex(
        self,
        company_id: UUID,
        branch_id: UUID,
        product_id: UUID,
        *,
        occurred_at_from: datetime | None,
        occurred_at_to: datetime | None,
        movement_type: str | None,
        origin_type: str | None,
        origin_id: UUID | None,
        page: int,
        page_size: int,
    ) -> Page:
        return self._repository.list_kardex(
            company_id,
            branch_id,
            product_id,
            occurred_at_from=occurred_at_from,
            occurred_at_to=occurred_at_to,
            movement_type=movement_type,
            origin_type=origin_type,
            origin_id=origin_id,
            page=page,
            page_size=page_size,
        )

    def operation(self, company_id: UUID, operation_id: UUID) -> StoredOperation:
        stored = self._repository.get_operation(operation_id, company_id)
        if stored is None:
            raise NotFoundError()
        return stored

    def operation_by_key(self, company_id: UUID, operation_key: UUID) -> StoredOperation:
        stored = self._repository.get_operation_by_key(operation_key, company_id)
        if stored is None:
            raise NotFoundError()
        return stored
