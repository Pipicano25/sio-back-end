"""Repositorio de Inventory Service (research.md R-03, R-04, R-05, R-08).

`apply_operation` aplica una operación o un reverso en **una sola transacción**:

1. `SET LOCAL lock_timeout`.
2. `INSERT INTO inventory_operations … ON CONFLICT (operation_key) DO NOTHING
   RETURNING id`: si otra transacción ya registró la clave, no inserta →
   `ROLLBACK` y `KeyTakenError` (quien llama vuelve a consultar la clave). Si esa
   otra transacción aún no confirma, PostgreSQL hace esperar esta inserción.
3. Saldos de los productos afectados: `INSERT … ON CONFLICT DO NOTHING` de los que no
   existen y `SELECT … FOR UPDATE` **en orden de `company_product_id`** (orden global:
   sin interbloqueos entre operaciones que comparten productos).
4. Con las filas bloqueadas, cada línea calcula su saldo nuevo y recibe
   `balance_sequence = version + 1`; el saldo queda con `version` = último
   correlativo. No se usa ninguna `SEQUENCE`: si la transacción se revierte, también
   se revierte el aumento de `version` y no quedan huecos.
5. Saldo negativo → `InsufficientStockError` y `ROLLBACK` (nada aplicado).
6. Movimientos, saldos y el gancho `on_applied` (evento de auditoría en la outbox,
   FR-071) en la misma transacción; `COMMIT`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from inventory_service.application.exceptions import (
    AlreadyReversedError,
    InsufficientStockError,
    ValidationFailedError,
    field_error,
)
from inventory_service.domain.balance_math import MOVEMENT_TYPE_BY_OPERATION, apply_movement
from inventory_service.domain.quantities import in_range
from inventory_service.infrastructure.database import set_lock_timeout
from inventory_service.infrastructure.models import InventoryBalance, InventoryMovement, InventoryOperation

REVERSES_CONSTRAINT = "uq_inventory_operations_reverses"


class KeyTakenError(Exception):
    """Otra transacción registró la misma clave de operación primero (R-03 paso 4)."""


@dataclass(frozen=True, slots=True)
class NewLine:
    index: int
    origin_detail_id: UUID
    company_product_id: UUID
    quantity: Decimal
    unit_cost: Decimal | None
    reversed_movement_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class NewOperation:
    operation_key: UUID
    client_id: str
    created_by: str
    operation_type: str
    company_id: UUID
    branch_id: UUID
    origin_type: str
    origin_id: UUID
    application_user_id: UUID
    correlation_id: UUID
    reason: str | None
    reverses_operation_id: UUID | None
    request_hash: str
    lines: Sequence[NewLine]


@dataclass(frozen=True, slots=True)
class MovementRow:
    id: UUID
    operation_id: UUID
    company_id: UUID
    branch_id: UUID
    company_product_id: UUID
    movement_type: str
    quantity: Decimal
    previous_balance: Decimal
    new_balance: Decimal
    balance_sequence: int
    unit_cost: Decimal | None
    origin_type: str
    origin_id: UUID
    origin_detail_id: UUID
    line_index: int
    application_user_id: UUID
    correlation_id: UUID
    reason: str | None
    reversed_movement_id: UUID | None
    created_at: datetime
    created_by: str


@dataclass(slots=True)
class StoredOperation:
    id: UUID
    operation_key: UUID
    requested_by_client: str
    operation_type: str
    company_id: UUID
    branch_id: UUID
    origin_type: str
    origin_id: UUID
    application_user_id: UUID
    correlation_id: UUID
    reason: str | None
    reverses_operation_id: UUID | None
    request_hash: str
    created_at: datetime
    created_by: str
    movements: list[MovementRow] = field(default_factory=list)
    reversed_by_operation_id: UUID | None = None

    @property
    def balances_after(self) -> dict[UUID, Decimal]:
        """Saldo de cada producto tras la operación (el del momento en que se aplicó)."""
        result: dict[UUID, Decimal] = {}
        for movement in sorted(self.movements, key=lambda m: m.line_index):
            result[movement.company_product_id] = movement.new_balance
        return result


@dataclass(frozen=True, slots=True)
class BalanceRow:
    company_id: UUID
    branch_id: UUID
    company_product_id: UUID
    quantity: Decimal
    version: int
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class Page:
    items: list[Any]
    total_records: int


OnApplied = Callable[[Session, StoredOperation], None]


def _movement(model: InventoryMovement) -> MovementRow:
    return MovementRow(**{name: getattr(model, name) for name in MovementRow.__dataclass_fields__})


class SqlInventoryRepository:
    """Acceso a `inventory_operations`, `inventory_balances` e `inventory_movements`."""

    def __init__(self, session: Session, *, lock_timeout_ms: int) -> None:
        self._session = session
        self._lock_timeout_ms = lock_timeout_ms

    # Lectura de operaciones ---------------------------------------------------

    def _load(self, operation: InventoryOperation | None) -> StoredOperation | None:
        if operation is None:
            return None

        movements = self._session.scalars(
            select(InventoryMovement)
            .where(InventoryMovement.operation_id == operation.id)
            .order_by(InventoryMovement.line_index)
        ).all()
        reversed_by = self._session.scalar(
            select(InventoryOperation.id).where(InventoryOperation.reverses_operation_id == operation.id)
        )
        return StoredOperation(
            id=operation.id,
            operation_key=operation.operation_key,
            requested_by_client=operation.requested_by_client,
            operation_type=operation.operation_type,
            company_id=operation.company_id,
            branch_id=operation.branch_id,
            origin_type=operation.origin_type,
            origin_id=operation.origin_id,
            application_user_id=operation.application_user_id,
            correlation_id=operation.correlation_id,
            reason=operation.reason,
            reverses_operation_id=operation.reverses_operation_id,
            request_hash=operation.request_hash.strip(),
            created_at=operation.created_at,
            created_by=operation.created_by,
            movements=[_movement(m) for m in movements],
            reversed_by_operation_id=reversed_by,
        )

    def find_by_key(self, operation_key: UUID) -> StoredOperation | None:
        try:
            return self._load(
                self._session.scalar(select(InventoryOperation).where(InventoryOperation.operation_key == operation_key))
            )
        finally:
            self._session.rollback()

    def get_operation(self, operation_id: UUID, company_id: UUID) -> StoredOperation | None:
        """Operación por `id` **dentro de la empresa indicada** (FR-034, RC-06)."""
        try:
            return self._load(
                self._session.scalar(
                    select(InventoryOperation).where(
                        InventoryOperation.id == operation_id, InventoryOperation.company_id == company_id
                    )
                )
            )
        finally:
            self._session.rollback()

    def get_operation_by_key(self, operation_key: UUID, company_id: UUID) -> StoredOperation | None:
        try:
            return self._load(
                self._session.scalar(
                    select(InventoryOperation).where(
                        InventoryOperation.operation_key == operation_key, InventoryOperation.company_id == company_id
                    )
                )
            )
        finally:
            self._session.rollback()

    # Aplicación ---------------------------------------------------------------

    def apply_operation(self, operation: NewOperation, on_applied: OnApplied | None = None) -> StoredOperation:
        session = self._session
        try:
            stored = self._apply(operation)
            if on_applied is not None:
                on_applied(session, stored)
            session.commit()
            return stored
        except IntegrityError as error:
            session.rollback()
            if REVERSES_CONSTRAINT in str(error.orig):
                raise AlreadyReversedError() from None
            raise
        except BaseException:
            session.rollback()
            raise

    def _apply(self, operation: NewOperation) -> StoredOperation:
        session = self._session
        set_lock_timeout(session, self._lock_timeout_ms)
        now = session.scalar(select(func.now()))

        operation_id = session.scalar(
            insert(InventoryOperation)
            .values(
                operation_key=operation.operation_key,
                requested_by_client=operation.client_id,
                operation_type=operation.operation_type,
                company_id=operation.company_id,
                branch_id=operation.branch_id,
                origin_type=operation.origin_type,
                origin_id=operation.origin_id,
                application_user_id=operation.application_user_id,
                correlation_id=operation.correlation_id,
                reason=operation.reason,
                reverses_operation_id=operation.reverses_operation_id,
                line_count=len(operation.lines),
                request_hash=operation.request_hash,
                created_at=now,
                created_by=operation.created_by,
            )
            .on_conflict_do_nothing(index_elements=["operation_key"])
            .returning(InventoryOperation.id)
        )

        if operation_id is None:
            raise KeyTakenError()

        balances = self._lock_balances(operation, now)
        movement_type = MOVEMENT_TYPE_BY_OPERATION[operation.operation_type]
        running = {product: (row.quantity, row.version) for product, row in balances.items()}
        shortages: list[dict[str, Any]] = []
        range_errors: list[dict[str, str]] = []
        rows: list[dict[str, Any]] = []

        for item in operation.lines:
            available, version = running[item.company_product_id]
            new_balance = apply_movement(available, movement_type, item.quantity)

            if new_balance < 0:
                shortages.append(
                    {
                        "index": item.index,
                        "company_product_id": str(item.company_product_id),
                        "available": f"{available:.4f}",
                        "requested": f"{item.quantity:.4f}",
                    }
                )
                continue

            if not in_range(new_balance):
                range_errors.append(
                    field_error(
                        f"lines[{item.index}].quantity",
                        "QUANTITY_OUT_OF_RANGE",
                        "El saldo resultante supera el máximo permitido.",
                    )
                )
                continue

            sequence = version + 1  # asignado con la fila de saldo ya bloqueada (R-04)
            running[item.company_product_id] = (new_balance, sequence)
            rows.append(
                {
                    "id": uuid4(),
                    "operation_id": operation_id,
                    "company_id": operation.company_id,
                    "branch_id": operation.branch_id,
                    "company_product_id": item.company_product_id,
                    "movement_type": movement_type,
                    "quantity": item.quantity,
                    "previous_balance": available,
                    "new_balance": new_balance,
                    "balance_sequence": sequence,
                    "unit_cost": item.unit_cost,
                    "origin_type": operation.origin_type,
                    "origin_id": operation.origin_id,
                    "origin_detail_id": item.origin_detail_id,
                    "line_index": item.index,
                    "application_user_id": operation.application_user_id,
                    "correlation_id": operation.correlation_id,
                    "reason": operation.reason,
                    "reversed_movement_id": item.reversed_movement_id,
                    "created_at": now,
                    "created_by": operation.created_by,
                    "updated_at": now,
                    "updated_by": operation.created_by,
                }
            )

        if shortages:
            raise InsufficientStockError(shortages)

        if range_errors:
            raise ValidationFailedError(range_errors)

        session.execute(insert(InventoryMovement), rows)

        for product, (quantity, version) in running.items():
            if version != balances[product].version:
                session.execute(
                    update(InventoryBalance)
                    .where(
                        InventoryBalance.company_id == operation.company_id,
                        InventoryBalance.branch_id == operation.branch_id,
                        InventoryBalance.company_product_id == product,
                    )
                    .values(quantity=quantity, version=version, updated_at=now, updated_by=operation.created_by)
                )

        return StoredOperation(
            id=operation_id,
            operation_key=operation.operation_key,
            requested_by_client=operation.client_id,
            operation_type=operation.operation_type,
            company_id=operation.company_id,
            branch_id=operation.branch_id,
            origin_type=operation.origin_type,
            origin_id=operation.origin_id,
            application_user_id=operation.application_user_id,
            correlation_id=operation.correlation_id,
            reason=operation.reason,
            reverses_operation_id=operation.reverses_operation_id,
            request_hash=operation.request_hash,
            created_at=now,
            created_by=operation.created_by,
            movements=[_row(row) for row in rows],
        )

    def _lock_balances(self, operation: NewOperation, now: datetime) -> dict[UUID, BalanceRow]:
        products = sorted({item.company_product_id for item in operation.lines}, key=str)
        session = self._session
        session.execute(
            insert(InventoryBalance)
            .values(
                [
                    {
                        "company_id": operation.company_id,
                        "branch_id": operation.branch_id,
                        "company_product_id": product,
                        "quantity": Decimal(0),
                        "version": 0,
                        "created_at": now,
                        "created_by": operation.created_by,
                        "updated_at": now,
                        "updated_by": operation.created_by,
                    }
                    for product in products
                ]
            )
            .on_conflict_do_nothing(index_elements=["company_id", "branch_id", "company_product_id"])
        )
        locked = session.execute(
            select(InventoryBalance)
            .where(
                InventoryBalance.company_id == operation.company_id,
                InventoryBalance.branch_id == operation.branch_id,
                InventoryBalance.company_product_id.in_(products),
            )
            .order_by(InventoryBalance.company_product_id)
            .with_for_update()
        ).scalars()
        return {
            row.company_product_id: BalanceRow(
                row.company_id, row.branch_id, row.company_product_id, row.quantity, row.version, row.updated_at
            )
            for row in locked
        }

    # Consultas ----------------------------------------------------------------

    def get_balance(self, company_id: UUID, branch_id: UUID, product_id: UUID) -> BalanceRow | None:
        try:
            row = self._session.scalar(
                select(InventoryBalance).where(
                    InventoryBalance.company_id == company_id,
                    InventoryBalance.branch_id == branch_id,
                    InventoryBalance.company_product_id == product_id,
                )
            )
            return _balance(row) if row is not None else None
        finally:
            self._session.rollback()

    def get_balances(self, company_id: UUID, branch_id: UUID, product_ids: Iterable[UUID]) -> dict[UUID, BalanceRow]:
        ids = list(product_ids)
        try:
            rows = self._session.scalars(
                select(InventoryBalance).where(
                    InventoryBalance.company_id == company_id,
                    InventoryBalance.branch_id == branch_id,
                    InventoryBalance.company_product_id.in_(ids),
                )
            ).all()
            return {row.company_product_id: _balance(row) for row in rows}
        finally:
            self._session.rollback()

    def list_balances(
        self,
        company_id: UUID,
        branch_id: UUID,
        *,
        product_id: UUID | None,
        in_stock_only: bool,
        page: int,
        page_size: int,
    ) -> Page:
        conditions = [InventoryBalance.company_id == company_id, InventoryBalance.branch_id == branch_id]
        if product_id is not None:
            conditions.append(InventoryBalance.company_product_id == product_id)
        if in_stock_only:
            conditions.append(InventoryBalance.quantity > 0)
        try:
            total = self._session.scalar(select(func.count()).select_from(InventoryBalance).where(and_(*conditions)))
            rows = self._session.scalars(
                select(InventoryBalance)
                .where(and_(*conditions))
                .order_by(InventoryBalance.company_product_id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return Page([_balance(row) for row in rows], total or 0)
        finally:
            self._session.rollback()

    def list_kardex(
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
        conditions = [
            InventoryMovement.company_id == company_id,
            InventoryMovement.branch_id == branch_id,
            InventoryMovement.company_product_id == product_id,
        ]
        if occurred_at_from is not None:
            conditions.append(InventoryMovement.created_at >= occurred_at_from)
        if occurred_at_to is not None:
            conditions.append(InventoryMovement.created_at <= occurred_at_to)
        if movement_type is not None:
            conditions.append(InventoryMovement.movement_type == movement_type)
        if origin_type is not None:
            conditions.append(InventoryMovement.origin_type == origin_type)
        if origin_id is not None:
            conditions.append(InventoryMovement.origin_id == origin_id)
        try:
            total = self._session.scalar(select(func.count()).select_from(InventoryMovement).where(and_(*conditions)))
            rows = self._session.scalars(
                select(InventoryMovement)
                .where(and_(*conditions))
                .order_by(InventoryMovement.balance_sequence)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return Page([_movement(row) for row in rows], total or 0)
        finally:
            self._session.rollback()


def _row(values: dict[str, Any]) -> MovementRow:
    return MovementRow(**{name: values[name] for name in MovementRow.__dataclass_fields__})


def _balance(row: InventoryBalance) -> BalanceRow:
    return BalanceRow(row.company_id, row.branch_id, row.company_product_id, row.quantity, row.version, row.updated_at)
