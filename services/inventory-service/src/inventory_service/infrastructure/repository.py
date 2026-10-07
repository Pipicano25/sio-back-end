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

013 (R-02, R-03): cada línea trae su tipo de movimiento (los ajustes mezclan
positivos y negativos) y la valoración FIFO ocurre **en la misma transacción y
bajo el mismo bloqueo** (`valuation_repository.LayerBook`): capas y consumos,
`unit_cost`, `movement_value` y `cost_known` de cada movimiento, y
`inventory_value`, `average_unit_cost` y `has_unknown_cost` de cada saldo. Orden
de bloqueos: (conteo, si lo hay) → saldos → capas. Si Σ capas abiertas ≠ saldo
antes del `COMMIT`, todo se revierte (`ValuationInvariantError`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, bindparam, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from inventory_service.application.exceptions import (
    ActivePolicyExistsError,
    AlreadyReversedError,
    CountAlreadyInProgressError,
    CountNotInProgressError,
    InsufficientStockError,
    InvalidCountTransitionError,
    NotFoundError,
    PolicyAlreadyExistsError,
    VersionConflictError,
    ValidationFailedError,
    ValuationInvariantError,
    field_error,
)
from inventory_service.domain.balance_math import MOVEMENT_TYPE_BY_OPERATION, apply_movement
from inventory_service.domain.quantities import in_range
from inventory_service.infrastructure.database import set_lock_timeout
from inventory_service.infrastructure.models import (
    CompanyInventoryPolicy,
    InventoryAdjustment,
    InventoryBalance,
    InventoryCount,
    InventoryCountDetail,
    InventoryMovement,
    InventoryOperation,
    InventoryPolicy,
)
from inventory_service.infrastructure.valuation_repository import MAX_MONEY, LayerBook, valuation_at

__all__ = ["ValuationInvariantError"]

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
    movement_type: str | None = None
    """`None` → el tipo por defecto de la operación (Fase A); los ajustes lo traen por línea."""
    cost_field: str | None = None
    """Campo de la solicitud para `UNIT_COST_REQUIRED` (`unit_cost`, `details[<id>].unit_cost`)."""


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
    currency_code: str | None = None
    """`default_currency` de la empresa: obligatoria si la operación crea capas (R-03b)."""


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
    movement_value: Decimal | None
    cost_known: bool | None
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
    valuation_after: dict[UUID, Any] = field(default_factory=dict)
    """`Valuation` de cada saldo tras la operación (vacío en operaciones anteriores a la valoración)."""

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
    inventory_value: Decimal = Decimal("0.00")
    average_unit_cost: Decimal | None = None
    has_unknown_cost: bool = False


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

    def _load(self, operation: InventoryOperation | None, *, with_valuation: bool = False) -> StoredOperation | None:
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
            valuation_after=self._valuation_after(operation, movements) if with_valuation else {},
        )

    def _valuation_after(self, operation: InventoryOperation, movements) -> dict[UUID, Any]:
        last: dict[UUID, InventoryMovement] = {}
        for movement in movements:
            if movement.movement_value is not None:
                last[movement.company_product_id] = movement
        return {
            product: valuation_at(
                self._session, operation.company_id, operation.branch_id, product, movement.balance_sequence
            )
            for product, movement in last.items()
        }

    def find_by_key(self, operation_key: UUID) -> StoredOperation | None:
        """Operación por clave con la valoración de aquel momento (respuesta idéntica de un reintento)."""
        try:
            return self._load(
                self._session.scalar(select(InventoryOperation).where(InventoryOperation.operation_key == operation_key)),
                with_valuation=True,
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

    def _apply(self, operation: NewOperation, *, now: datetime | None = None) -> StoredOperation:
        """Aplica dentro de la transacción en curso; con `now` dado, quien llama ya fijó el `lock_timeout`."""
        session = self._session
        if now is None:
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
        running = {product: (row.quantity, row.version) for product, row in balances.items()}
        shortages: list[dict[str, Any]] = []
        range_errors: list[dict[str, str]] = []
        rows: list[dict[str, Any]] = []

        for item in operation.lines:
            movement_type = item.movement_type or MOVEMENT_TYPE_BY_OPERATION[operation.operation_type]
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
                    "unit_cost": None,
                    "movement_value": None,
                    "cost_known": None,
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

        # Valoración FIFO bajo los mismos bloqueos (013 R-03): capas bloqueadas después de los saldos.
        book = LayerBook(
            session,
            company_id=operation.company_id,
            branch_id=operation.branch_id,
            now=now,
            actor=operation.created_by,
            currency_code=operation.currency_code,
        )
        lines = [
            _Line(item, item.movement_type or MOVEMENT_TYPE_BY_OPERATION[operation.operation_type])
            for item in operation.lines
        ]
        book.load(lines)
        book.check_entry_reversals(lines)

        if shortages:
            raise InsufficientStockError(shortages)

        if range_errors:
            raise ValidationFailedError(range_errors)

        cost_errors: list[dict[str, str]] = []
        for row, line in zip(rows, lines, strict=True):
            cost_errors.extend(book.value_line(row, line, origin_id=operation.origin_id))
        if cost_errors:
            raise ValidationFailedError(cost_errors)
        valuations = book.settle({product: quantity for product, (quantity, _) in running.items()})
        value_errors = [
            field_error(
                f"lines[{next(item.index for item in operation.lines if item.company_product_id == product)}].quantity",
                "QUANTITY_OUT_OF_RANGE",
                "El valor resultante del saldo supera el máximo permitido.",
            )
            for product, current in valuations.items()
            if current.value >= MAX_MONEY
        ]
        if value_errors:
            raise ValidationFailedError(value_errors)

        session.execute(insert(InventoryMovement), rows)
        book.persist()

        # Un solo `executemany` para todos los saldos (operaciones de hasta 1 000 líneas, SC-002).
        balances_table = InventoryBalance.__table__
        session.connection().execute(
            update(balances_table)
            .where(
                balances_table.c.company_id == operation.company_id,
                balances_table.c.branch_id == operation.branch_id,
                balances_table.c.company_product_id == bindparam("product"),
            )
            .values(
                quantity=bindparam("quantity"),
                version=bindparam("version"),
                inventory_value=bindparam("inventory_value"),
                average_unit_cost=bindparam("average_unit_cost"),
                has_unknown_cost=bindparam("has_unknown_cost"),
                updated_at=now,
                updated_by=operation.created_by,
            ),
            [
                {
                    "product": product,
                    "quantity": quantity,
                    "version": version,
                    "inventory_value": valuations[product].value,
                    "average_unit_cost": valuations[product].average_unit_cost,
                    "has_unknown_cost": valuations[product].has_unknown_cost,
                }
                for product, (quantity, version) in running.items()
            ],
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
            valuation_after=valuations,
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
    return BalanceRow(
        row.company_id,
        row.branch_id,
        row.company_product_id,
        row.quantity,
        row.version,
        row.updated_at,
        row.inventory_value,
        row.average_unit_cost,
        row.has_unknown_cost,
    )


@dataclass(frozen=True, slots=True)
class _Line:
    """Línea con su tipo de movimiento resuelto, para el libro de capas."""

    item: NewLine
    movement_type: str

    @property
    def index(self) -> int:
        return self.item.index

    @property
    def company_product_id(self) -> UUID:
        return self.item.company_product_id

    @property
    def quantity(self) -> Decimal:
        return self.item.quantity

    @property
    def unit_cost(self) -> Decimal | None:
        return self.item.unit_cost

    @property
    def reversed_movement_id(self) -> UUID | None:
        return self.item.reversed_movement_id

    @property
    def cost_field(self) -> str | None:
        return self.item.cost_field


# ==========================================================================
# Ajustes (013 R-02; `inventory_adjustments`)
# ==========================================================================


@dataclass(frozen=True, slots=True)
class AdjustmentRow:
    id: UUID
    operation_id: UUID
    movement_id: UUID
    company_id: UUID
    branch_id: UUID
    company_product_id: UUID
    adjustment_type: str
    quantity: Decimal
    reason: str
    previous_balance: Decimal
    new_balance: Decimal
    unit_cost: Decimal
    adjustment_value: Decimal
    inventory_count_id: UUID | None
    application_user_id: UUID
    created_at: datetime
    created_by: str


def adjustment_values(
    adjustment_id: UUID,
    stored: StoredOperation,
    movement: MovementRow,
    *,
    reason: str,
    application_user_id: UUID,
    inventory_count_id: UUID | None = None,
) -> dict[str, Any]:
    """Fila de `inventory_adjustments` a partir del movimiento ya valorizado (inmutable: `updated_*` = `created_*`)."""
    return {
        "id": adjustment_id,
        "operation_id": stored.id,
        "movement_id": movement.id,
        "company_id": stored.company_id,
        "branch_id": stored.branch_id,
        "company_product_id": movement.company_product_id,
        "adjustment_type": "POSITIVE" if movement.movement_type == "POSITIVE_ADJUSTMENT" else "NEGATIVE",
        "quantity": movement.quantity,
        "reason": reason,
        "previous_balance": movement.previous_balance,
        "new_balance": movement.new_balance,
        "unit_cost": movement.unit_cost,
        "adjustment_value": movement.movement_value,
        "inventory_count_id": inventory_count_id,
        "application_user_id": application_user_id,
        "created_at": stored.created_at,
        "created_by": stored.created_by,
        "updated_at": stored.created_at,
        "updated_by": stored.created_by,
    }


def insert_adjustments(session: Session, rows: Sequence[dict[str, Any]]) -> None:
    if rows:
        session.execute(insert(InventoryAdjustment), list(rows))


def _adjustment(model: InventoryAdjustment) -> AdjustmentRow:
    return AdjustmentRow(**{name: getattr(model, name) for name in AdjustmentRow.__dataclass_fields__})


class AdjustmentQueries:
    """Lectura de ajustes con su movimiento (siempre acotada por empresa)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _with_movements(self, models: Sequence[InventoryAdjustment]) -> list[tuple[AdjustmentRow, MovementRow]]:
        ids = [model.movement_id for model in models]
        movements = {
            model.id: _movement(model)
            for model in self._session.scalars(select(InventoryMovement).where(InventoryMovement.id.in_(ids)))
        }
        return [(_adjustment(model), movements[model.movement_id]) for model in models]

    def get(self, company_id: UUID, adjustment_id: UUID) -> tuple[AdjustmentRow, MovementRow] | None:
        try:
            model = self._session.scalar(
                select(InventoryAdjustment).where(
                    InventoryAdjustment.id == adjustment_id, InventoryAdjustment.company_id == company_id
                )
            )
            return self._with_movements([model])[0] if model is not None else None
        finally:
            self._session.rollback()

    def by_operation(self, operation_id: UUID) -> list[tuple[AdjustmentRow, MovementRow]]:
        try:
            models = self._session.scalars(
                select(InventoryAdjustment)
                .where(InventoryAdjustment.operation_id == operation_id)
                .order_by(InventoryAdjustment.created_at, InventoryAdjustment.id)
            ).all()
            pairs = self._with_movements(models)
            return sorted(pairs, key=lambda pair: pair[1].line_index)
        finally:
            self._session.rollback()

    def by_count(self, count_id: UUID) -> list[tuple[AdjustmentRow, MovementRow]]:
        try:
            models = self._session.scalars(
                select(InventoryAdjustment).where(InventoryAdjustment.inventory_count_id == count_id)
            ).all()
            return sorted(self._with_movements(models), key=lambda pair: pair[1].line_index)
        finally:
            self._session.rollback()

    def list(
        self,
        company_id: UUID,
        *,
        branch_id: UUID | None,
        product_id: UUID | None,
        adjustment_type: str | None,
        count_id: UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
        page: int,
        page_size: int,
    ) -> Page:
        conditions = [InventoryAdjustment.company_id == company_id]
        if branch_id is not None:
            conditions.append(InventoryAdjustment.branch_id == branch_id)
        if product_id is not None:
            conditions.append(InventoryAdjustment.company_product_id == product_id)
        if adjustment_type is not None:
            conditions.append(InventoryAdjustment.adjustment_type == adjustment_type)
        if count_id is not None:
            conditions.append(InventoryAdjustment.inventory_count_id == count_id)
        if created_from is not None:
            conditions.append(InventoryAdjustment.created_at >= created_from)
        if created_to is not None:
            conditions.append(InventoryAdjustment.created_at <= created_to)
        try:
            total = self._session.scalar(select(func.count()).select_from(InventoryAdjustment).where(and_(*conditions)))
            models = self._session.scalars(
                select(InventoryAdjustment)
                .where(and_(*conditions))
                .order_by(InventoryAdjustment.created_at.desc(), InventoryAdjustment.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return Page(self._with_movements(models), total or 0)
        finally:
            self._session.rollback()


# ==========================================================================
# Conteos (013 R-10; `inventory_counts`, `inventory_count_details`)
# ==========================================================================

COUNT_IN_PROGRESS_INDEX = "uq_inventory_counts_in_progress"
COUNT_ADJUSTMENT_REASON = "Diferencia del conteo físico"
MAX_COUNT_DETAILS = 1000


@dataclass(frozen=True, slots=True)
class CountRow:
    id: UUID
    company_id: UUID
    branch_id: UUID
    status: str
    started_by_user_id: UUID
    started_at: datetime | None
    completed_by_user_id: UUID | None
    completed_at: datetime | None
    cancelled_by_user_id: UUID | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    operation_id: UUID | None
    observations: str | None
    version: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


@dataclass(frozen=True, slots=True)
class CountDetailRow:
    id: UUID
    inventory_count_id: UUID
    company_product_id: UUID
    system_quantity_snapshot: Decimal
    counted_quantity: Decimal
    difference_quantity: Decimal
    unit_cost: Decimal | None
    inventory_adjustment_id: UUID | None
    counted_by_user_id: UUID
    counted_at: datetime


def _count(model: InventoryCount) -> CountRow:
    return CountRow(**{name: getattr(model, name) for name in CountRow.__dataclass_fields__})


def _detail(model: InventoryCountDetail) -> CountDetailRow:
    return CountDetailRow(**{name: getattr(model, name) for name in CountDetailRow.__dataclass_fields__})


CountHook = Callable[[Session, CountRow], None]
CompletionHook = Callable[[Session, CountRow, "StoredOperation | None", list], None]
BuildCompletion = Callable[[CountRow, list], "NewOperation | None"]


class SqlCountRepository:
    """Conteos físicos. Toda transición bloquea la fila del conteo (`SELECT … FOR UPDATE`).

    La finalización aplica la operación `ADJUSTMENT`/`COUNT` con el motor en la
    **misma** transacción y sesión, en el orden de bloqueos conteo → saldos → capas.
    """

    def __init__(self, session: Session, engine: SqlInventoryRepository, *, lock_timeout_ms: int) -> None:
        self._session = session
        self._engine = engine
        self._lock_timeout_ms = lock_timeout_ms

    # Lectura ----------------------------------------------------------------------

    def get(self, company_id: UUID, count_id: UUID) -> CountRow | None:
        try:
            model = self._session.scalar(
                select(InventoryCount).where(InventoryCount.id == count_id, InventoryCount.company_id == company_id)
            )
            return _count(model) if model is not None else None
        finally:
            self._session.rollback()

    def details(self, count_id: UUID) -> list[CountDetailRow]:
        try:
            return [
                _detail(model)
                for model in self._session.scalars(
                    select(InventoryCountDetail)
                    .where(InventoryCountDetail.inventory_count_id == count_id)
                    .order_by(InventoryCountDetail.company_product_id)
                )
            ]
        finally:
            self._session.rollback()

    def list(self, company_id: UUID, *, branch_id: UUID | None, status: str | None, page: int, page_size: int) -> Page:
        conditions = [InventoryCount.company_id == company_id]
        if branch_id is not None:
            conditions.append(InventoryCount.branch_id == branch_id)
        if status is not None:
            conditions.append(InventoryCount.status == status)
        try:
            total = self._session.scalar(select(func.count()).select_from(InventoryCount).where(and_(*conditions)))
            models = self._session.scalars(
                select(InventoryCount)
                .where(and_(*conditions))
                .order_by(InventoryCount.created_at.desc(), InventoryCount.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return Page([_count(model) for model in models], total or 0)
        finally:
            self._session.rollback()

    # Escritura --------------------------------------------------------------------

    def _begin(self) -> datetime:
        set_lock_timeout(self._session, self._lock_timeout_ms)
        return self._session.scalar(select(func.now()))

    def _lock(self, company_id: UUID, count_id: UUID, expected_version: int | None) -> InventoryCount:
        model = self._session.scalar(
            select(InventoryCount)
            .where(InventoryCount.id == count_id, InventoryCount.company_id == company_id)
            .with_for_update()
        )
        if model is None:
            raise NotFoundError()
        if expected_version is not None and model.version != expected_version:
            raise VersionConflictError()
        return model

    def _finish(self, model: InventoryCount, hook: CountHook | None) -> CountRow:
        session = self._session
        session.flush()
        row = _count(model)
        if hook is not None:
            hook(session, row)
        session.commit()
        return row

    def create(self, company_id: UUID, branch_id: UUID, user_id: UUID, observations: str | None, actor: str) -> CountRow:
        session = self._session
        try:
            now = self._begin()
            model = InventoryCount(
                id=uuid4(),
                company_id=company_id,
                branch_id=branch_id,
                status="DRAFT",
                started_by_user_id=user_id,
                observations=observations,
                version=1,
                created_at=now,
                created_by=actor,
                updated_at=now,
                updated_by=actor,
            )
            session.add(model)
            return self._finish(model, None)
        except BaseException:
            session.rollback()
            raise

    def start(self, company_id: UUID, count_id: UUID, version: int, actor: str, hook: CountHook) -> CountRow:
        session = self._session
        try:
            now = self._begin()
            model = self._lock(company_id, count_id, version)
            if model.status != "DRAFT":
                raise InvalidCountTransitionError()
            model.status = "IN_PROGRESS"
            model.started_at = now
            model.version += 1
            model.updated_at, model.updated_by = now, actor
            return self._finish(model, hook)
        except IntegrityError as error:
            session.rollback()
            if COUNT_IN_PROGRESS_INDEX in str(error.orig):
                raise CountAlreadyInProgressError() from None
            raise
        except BaseException:
            session.rollback()
            raise

    def cancel(
        self, company_id: UUID, count_id: UUID, version: int, reason: str, user_id: UUID, actor: str, hook: CountHook
    ) -> CountRow:
        session = self._session
        try:
            now = self._begin()
            model = self._lock(company_id, count_id, version)
            if model.status not in ("DRAFT", "IN_PROGRESS"):
                raise InvalidCountTransitionError()
            model.status = "CANCELLED"
            model.cancelled_by_user_id = user_id
            model.cancelled_at = now
            model.cancel_reason = reason
            model.version += 1
            model.updated_at, model.updated_by = now, actor
            return self._finish(model, hook)
        except BaseException:
            session.rollback()
            raise

    def register_detail(
        self,
        company_id: UUID,
        count_id: UUID,
        product_id: UUID,
        counted: Decimal,
        unit_cost: Decimal | None,
        user_id: UUID,
        actor: str,
    ) -> CountDetailRow:
        """Upsert del producto contado con el saldo vigente como snapshot (DS-08)."""
        session = self._session
        try:
            now = self._begin()
            model = self._lock(company_id, count_id, None)
            if model.status != "IN_PROGRESS":
                raise CountNotInProgressError()
            others = session.scalar(
                select(func.count())
                .select_from(InventoryCountDetail)
                .where(
                    InventoryCountDetail.inventory_count_id == count_id,
                    InventoryCountDetail.company_product_id != product_id,
                )
            )
            if others >= MAX_COUNT_DETAILS:
                raise ValidationFailedError(
                    [
                        field_error(
                            "company_product_id",
                            "COUNT_DETAILS_LIMIT",
                            f"Un conteo admite a lo sumo {MAX_COUNT_DETAILS} productos.",
                        )
                    ]
                )
            snapshot = session.scalar(
                select(InventoryBalance.quantity).where(
                    InventoryBalance.company_id == company_id,
                    InventoryBalance.branch_id == model.branch_id,
                    InventoryBalance.company_product_id == product_id,
                )
            )
            snapshot = snapshot if snapshot is not None else Decimal(0)
            values = {
                "system_quantity_snapshot": snapshot,
                "counted_quantity": counted,
                "difference_quantity": counted - snapshot,
                "unit_cost": unit_cost,
                "counted_by_user_id": user_id,
                "counted_at": now,
                "updated_at": now,
                "updated_by": actor,
            }
            detail_id = session.scalar(
                insert(InventoryCountDetail)
                .values(
                    id=uuid4(),
                    inventory_count_id=count_id,
                    company_product_id=product_id,
                    created_at=now,
                    created_by=actor,
                    **values,
                )
                .on_conflict_do_update(constraint="uq_inventory_count_details_product", set_=values)
                .returning(InventoryCountDetail.id)
            )
            row = _detail(session.get(InventoryCountDetail, detail_id, populate_existing=True))
            session.commit()
            return row
        except BaseException:
            session.rollback()
            raise

    def complete(
        self,
        company_id: UUID,
        count_id: UUID,
        version: int,
        user_id: UUID,
        actor: str,
        build: BuildCompletion,
        hook: CompletionHook,
    ) -> tuple[CountRow, StoredOperation | None]:
        """Conteo → operación de ajustes → ajustes → detalles → estado, en **una** transacción (RC-13)."""
        session = self._session
        try:
            now = self._begin()
            model = self._lock(company_id, count_id, version)
            if model.status != "IN_PROGRESS":
                raise CountNotInProgressError()
            details = [
                _detail(item)
                for item in session.scalars(
                    select(InventoryCountDetail)
                    .where(InventoryCountDetail.inventory_count_id == count_id)
                    .order_by(InventoryCountDetail.company_product_id)
                )
            ]
            if not details:
                raise ValidationFailedError(
                    [field_error("details", "COUNT_WITHOUT_DETAILS", "El conteo no tiene productos registrados.")]
                )

            operation = build(_count(model), details)
            stored: StoredOperation | None = None
            rows: list[dict[str, Any]] = []
            if operation is not None:
                stored = self._engine._apply(operation, now=now)
                links: list[tuple[UUID, UUID]] = []
                for movement in stored.movements:
                    adjustment_id = uuid4()
                    rows.append(
                        adjustment_values(
                            adjustment_id,
                            stored,
                            movement,
                            reason=COUNT_ADJUSTMENT_REASON,
                            application_user_id=user_id,
                            inventory_count_id=count_id,
                        )
                    )
                    links.append((movement.origin_detail_id, adjustment_id))
                insert_adjustments(session, rows)
                # El enlace se escribe con el conteo aún `IN_PROGRESS` (el trigger de detalles lo permite).
                details_table = InventoryCountDetail.__table__
                session.connection().execute(
                    update(details_table)
                    .where(details_table.c.id == bindparam("detail_id"))
                    .values(inventory_adjustment_id=bindparam("adjustment_id"), updated_at=now, updated_by=actor),
                    [{"detail_id": detail_id, "adjustment_id": adjustment_id} for detail_id, adjustment_id in links],
                )

            model.status = "COMPLETED"
            model.completed_by_user_id = user_id
            model.completed_at = now
            model.operation_id = stored.id if stored is not None else None
            model.version += 1
            model.updated_at, model.updated_by = now, actor
            session.flush()
            row = _count(model)
            hook(session, row, stored, rows)
            session.commit()
            return row, stored
        except BaseException:
            session.rollback()
            raise


# ==========================================================================
# Políticas (013 R-06, R-07; `company_inventory_policies`, `inventory_policies`)
# ==========================================================================

COMPANY_POLICY_UNIQUE = "uq_company_inventory_policies_company"
ACTIVE_POLICY_INDEX = "uq_inventory_policies_active"
COMPANY_POLICY_FIELDS = ("inventory_system", "valuation_method", "replenishment_strategy")
PRODUCT_POLICY_FIELDS = (
    "minimum_stock",
    "target_stock",
    "service_level",
    "safety_stock_method",
    "calculation_window_days",
    "replenishment_mode",
    "auto_purchase_enabled",
)


@dataclass(frozen=True, slots=True)
class CompanyPolicyRow:
    id: UUID
    company_id: UUID
    inventory_system: str
    valuation_method: str
    replenishment_strategy: str
    is_active: bool
    version: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


@dataclass(frozen=True, slots=True)
class ProductPolicyRow:
    id: UUID
    company_id: UUID
    branch_id: UUID
    company_product_id: UUID
    minimum_stock: Decimal
    target_stock: Decimal | None
    service_level: Decimal | None
    safety_stock_method: str
    calculation_window_days: int
    replenishment_mode: str
    auto_purchase_enabled: bool
    is_active: bool
    version: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


PolicyHook = Callable[[Session, Any, Any], None]
"""Recibe (sesión, valores anteriores o `None`, fila nueva) para el evento de auditoría."""


def _policy_row(row_type, model):
    return row_type(**{name: getattr(model, name) for name in row_type.__dataclass_fields__})


class SqlPolicyRepository:
    """Políticas mutables por la API con `version` (Principio VII); sin eliminación (D7)."""

    def __init__(self, session: Session, *, lock_timeout_ms: int) -> None:
        self._session = session
        self._lock_timeout_ms = lock_timeout_ms

    def _begin(self) -> datetime:
        set_lock_timeout(self._session, self._lock_timeout_ms)
        return self._session.scalar(select(func.now()))

    def _commit(self, model, row_type, previous, hook: PolicyHook):
        session = self._session
        session.flush()
        row = _policy_row(row_type, model)
        hook(session, previous, row)
        session.commit()
        return row

    # Empresa ------------------------------------------------------------------------

    def company_policy(self, company_id: UUID) -> CompanyPolicyRow | None:
        try:
            model = self._session.scalar(
                select(CompanyInventoryPolicy).where(CompanyInventoryPolicy.company_id == company_id)
            )
            return _policy_row(CompanyPolicyRow, model) if model is not None else None
        finally:
            self._session.rollback()

    def create_company_policy(self, company_id: UUID, values: dict[str, Any], actor: str, hook: PolicyHook) -> CompanyPolicyRow:
        session = self._session
        try:
            now = self._begin()
            model = CompanyInventoryPolicy(
                id=uuid4(),
                company_id=company_id,
                is_active=True,
                version=1,
                created_at=now,
                created_by=actor,
                updated_at=now,
                updated_by=actor,
                **values,
            )
            session.add(model)
            return self._commit(model, CompanyPolicyRow, None, hook)
        except IntegrityError as error:
            session.rollback()
            if COMPANY_POLICY_UNIQUE in str(error.orig):
                raise PolicyAlreadyExistsError() from None
            raise
        except BaseException:
            session.rollback()
            raise

    def update_company_policy(
        self, company_id: UUID, version: int, values: dict[str, Any], actor: str, hook: PolicyHook
    ) -> CompanyPolicyRow:
        session = self._session
        try:
            now = self._begin()
            model = session.scalar(
                select(CompanyInventoryPolicy)
                .where(CompanyInventoryPolicy.company_id == company_id)
                .with_for_update()
            )
            if model is None:
                raise NotFoundError()
            if model.version != version:
                raise VersionConflictError()
            previous = _policy_row(CompanyPolicyRow, model)
            for name, value in values.items():
                setattr(model, name, value)
            model.version += 1
            model.updated_at, model.updated_by = now, actor
            return self._commit(model, CompanyPolicyRow, previous, hook)
        except BaseException:
            session.rollback()
            raise

    # Producto -------------------------------------------------------------------------

    def product_policy(self, company_id: UUID, policy_id: UUID) -> ProductPolicyRow | None:
        try:
            model = self._session.scalar(
                select(InventoryPolicy).where(InventoryPolicy.id == policy_id, InventoryPolicy.company_id == company_id)
            )
            return _policy_row(ProductPolicyRow, model) if model is not None else None
        finally:
            self._session.rollback()

    def list_product_policies(
        self,
        company_id: UUID,
        *,
        branch_id: UUID | None,
        product_id: UUID | None,
        is_active: bool | None,
        page: int,
        page_size: int,
    ) -> Page:
        conditions = [InventoryPolicy.company_id == company_id]
        if branch_id is not None:
            conditions.append(InventoryPolicy.branch_id == branch_id)
        if product_id is not None:
            conditions.append(InventoryPolicy.company_product_id == product_id)
        if is_active is not None:
            conditions.append(InventoryPolicy.is_active.is_(is_active))
        try:
            total = self._session.scalar(select(func.count()).select_from(InventoryPolicy).where(and_(*conditions)))
            models = self._session.scalars(
                select(InventoryPolicy)
                .where(and_(*conditions))
                .order_by(InventoryPolicy.branch_id, InventoryPolicy.company_product_id, InventoryPolicy.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return Page([_policy_row(ProductPolicyRow, model) for model in models], total or 0)
        finally:
            self._session.rollback()

    def create_product_policy(
        self, company_id: UUID, branch_id: UUID, product_id: UUID, values: dict[str, Any], actor: str, hook: PolicyHook
    ) -> ProductPolicyRow:
        session = self._session
        try:
            now = self._begin()
            model = InventoryPolicy(
                id=uuid4(),
                company_id=company_id,
                branch_id=branch_id,
                company_product_id=product_id,
                is_active=True,
                version=1,
                created_at=now,
                created_by=actor,
                updated_at=now,
                updated_by=actor,
                **values,
            )
            session.add(model)
            return self._commit(model, ProductPolicyRow, None, hook)
        except IntegrityError as error:
            session.rollback()
            if ACTIVE_POLICY_INDEX in str(error.orig):
                raise ActivePolicyExistsError() from None
            raise
        except BaseException:
            session.rollback()
            raise

    def _lock_product_policy(self, company_id: UUID, policy_id: UUID, version: int) -> InventoryPolicy:
        model = self._session.scalar(
            select(InventoryPolicy)
            .where(InventoryPolicy.id == policy_id, InventoryPolicy.company_id == company_id)
            .with_for_update()
        )
        if model is None:
            raise NotFoundError()
        if model.version != version:
            raise VersionConflictError()
        return model

    def update_product_policy(
        self, company_id: UUID, policy_id: UUID, version: int, values: dict[str, Any], actor: str, hook: PolicyHook
    ) -> ProductPolicyRow:
        session = self._session
        try:
            now = self._begin()
            model = self._lock_product_policy(company_id, policy_id, version)
            previous = _policy_row(ProductPolicyRow, model)
            for name, value in values.items():
                setattr(model, name, value)
            model.version += 1
            model.updated_at, model.updated_by = now, actor
            return self._commit(model, ProductPolicyRow, previous, hook)
        except BaseException:
            session.rollback()
            raise

    def deactivate_product_policy(
        self, company_id: UUID, policy_id: UUID, version: int, actor: str, hook: PolicyHook
    ) -> ProductPolicyRow:
        session = self._session
        try:
            now = self._begin()
            model = self._lock_product_policy(company_id, policy_id, version)
            previous = _policy_row(ProductPolicyRow, model)
            model.is_active = False
            model.version += 1
            model.updated_at, model.updated_by = now, actor
            return self._commit(model, ProductPolicyRow, previous, hook)
        except BaseException:
            session.rollback()
            raise
