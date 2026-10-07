"""Capas de costo y consumos FIFO dentro de la transacción del motor (013 R-03, R-04).

`LayerBook` trabaja **después** de que el repositorio bloqueó los saldos de la
operación (orden de `company_product_id`) y **antes** del `COMMIT`:

1. Lee, sin bloquear, los datos que la operación necesita además de las capas
   abiertas: consumos originales de las salidas que se revierten, capas de las
   entradas que se revierten, aperturas y la capa más reciente de los productos
   con ajuste positivo. Todas esas filas solo cambian con su saldo bloqueado.
2. Bloquea con **una** sentencia `SELECT … FOR UPDATE` las capas abiertas de los
   productos y las capas referidas, en orden global `company_product_id`,
   `received_at`, `id` (sin interbloqueos entre operaciones).
3. Valora cada línea en orden (`pkg/domain/fifo.py`) mutando el estado en memoria.
4. Verifica RC-15 (Σ capas abiertas = saldo) por producto; si falla, la
   transacción se revierte completa (`ValuationInvariantError`).
5. Escribe capas nuevas, capas modificadas y consumos; el repositorio escribe
   movimientos y saldos en la misma transacción.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import bindparam, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import distinct_on, insert
from sqlalchemy.orm import Session

from inventory_service.application.exceptions import (
    EntryLayerConsumedError,
    OutputNotValuedError,
    ValuationInvariantError,
    field_error,
)
from inventory_service.domain.balance_math import (
    MOVEMENT_ENTRY_REVERSAL,
    MOVEMENT_OUTPUT_REVERSAL,
    NEGATIVE_ADJUSTMENT,
    POSITIVE_ADJUSTMENT,
    PURCHASE_ENTRY,
    SALE_OUTPUT,
)
from inventory_service.domain.fifo import (
    ADJUSTMENT,
    CONSUME,
    ENTRY,
    ENTRY_REVERSAL,
    OPENING,
    RESTORE,
    EntryLayerConsumed,
    Layer,
    LayersExhausted,
    OutputNotValued,
    Take,
    UnitCostRequired,
    Valuation,
    consume,
    positive_adjustment_cost,
    restore,
    reverse_entry,
    valuation,
)
from inventory_service.domain.rounding import line_value, output_unit_cost
from inventory_service.infrastructure.models import InventoryCostConsumption, InventoryCostLayer, InventoryMovement


MAX_MONEY = Decimal("1e16")
"""Límite exclusivo de `NUMERIC(18,2)` (valores de movimientos y saldos)."""


def _value_out_of_range(line: Any) -> dict[str, str]:
    return field_error(
        f"lines[{line.index}].quantity",
        "QUANTITY_OUT_OF_RANGE",
        "El valor resultante supera el máximo permitido.",
    )


@dataclass(slots=True)
class _NewLayer:
    layer: Layer
    company_product_id: UUID
    origin_movement_id: UUID
    origin_purchase_id: UUID | None
    origin_purchase_detail_id: UUID | None


@dataclass(frozen=True, slots=True)
class _Original:
    consumption_id: UUID
    take: Take


def _layer(model: InventoryCostLayer) -> Layer:
    return Layer(
        id=model.id,
        kind=model.layer_kind,
        original=model.original_quantity,
        remaining=model.remaining_quantity,
        unit_cost=model.unit_cost,
        cost_known=model.cost_known,
        received_at=model.received_at,
    )


class LayerBook:
    """Estado FIFO de los saldos bloqueados de una operación."""

    def __init__(
        self,
        session: Session,
        *,
        company_id: UUID,
        branch_id: UUID,
        now: datetime,
        actor: str,
        currency_code: str | None,
    ) -> None:
        self._session = session
        self._currency_code = currency_code
        self._company_id = company_id
        self._branch_id = branch_id
        self._now = now
        self._actor = actor
        self._layers: dict[UUID, Layer] = {}
        self._product_of: dict[UUID, UUID] = {}
        self._loaded_remaining: dict[UUID, Decimal] = {}
        self._entry_layer_of: dict[UUID, UUID] = {}
        self._opening_of: dict[UUID, UUID] = {}
        self._latest: dict[UUID, Layer] = {}
        self._originals: dict[UUID, list[_Original]] = {}
        self._new_layers: list[_NewLayer] = []
        self._consumptions: list[dict[str, Any]] = []

    # 1–2. Carga y bloqueo ------------------------------------------------------------

    def load(self, lines: Sequence[Any]) -> None:
        session = self._session
        scope = (
            InventoryCostLayer.company_id == self._company_id,
            InventoryCostLayer.branch_id == self._branch_id,
        )
        products = sorted({line.company_product_id for line in lines}, key=str)
        restored = [line.reversed_movement_id for line in lines if line.movement_type == MOVEMENT_OUTPUT_REVERSAL]
        retired = [line.reversed_movement_id for line in lines if line.movement_type == MOVEMENT_ENTRY_REVERSAL]
        adjusted = sorted(
            {line.company_product_id for line in lines if line.movement_type == POSITIVE_ADJUSTMENT}, key=str
        )
        targets: set[UUID] = set()

        if restored:
            rows = session.execute(
                select(InventoryCostConsumption, InventoryCostLayer.received_at)
                .join(InventoryCostLayer, InventoryCostLayer.id == InventoryCostConsumption.cost_layer_id)
                .where(
                    InventoryCostConsumption.movement_id.in_(restored),
                    InventoryCostConsumption.consumption_type == CONSUME,
                )
                .order_by(InventoryCostLayer.received_at, InventoryCostLayer.id)
            ).all()
            for consumption, _received_at in rows:
                take = Take(
                    consumption.cost_layer_id,
                    consumption.quantity,
                    consumption.unit_cost,
                    consumption.cost_known,
                    consumption.cost_amount,
                )
                self._originals.setdefault(consumption.movement_id, []).append(_Original(consumption.id, take))
                targets.add(consumption.cost_layer_id)

        if retired:
            for layer_id, movement_id in session.execute(
                select(InventoryCostLayer.id, InventoryCostLayer.origin_movement_id).where(
                    *scope, InventoryCostLayer.origin_movement_id.in_(retired)
                )
            ):
                self._entry_layer_of[movement_id] = layer_id
                targets.add(layer_id)
            for layer_id, product in session.execute(
                select(InventoryCostLayer.id, InventoryCostLayer.company_product_id).where(
                    *scope,
                    InventoryCostLayer.company_product_id.in_(products),
                    InventoryCostLayer.layer_kind == OPENING,
                )
            ):
                self._opening_of[product] = layer_id
                targets.add(layer_id)

        if adjusted:
            latest = session.scalars(
                select(InventoryCostLayer)
                .where(*scope, InventoryCostLayer.company_product_id.in_(adjusted))
                .order_by(
                    InventoryCostLayer.company_product_id,
                    InventoryCostLayer.received_at.desc(),
                    InventoryCostLayer.id.desc(),
                )
                .ext(distinct_on(InventoryCostLayer.company_product_id))
            ).all()
            for model in latest:
                self._latest[model.company_product_id] = _layer(model)

        open_or_target = InventoryCostLayer.status == "OPEN"
        if targets:
            open_or_target = or_(open_or_target, InventoryCostLayer.id.in_(sorted(targets, key=str)))

        locked = session.scalars(
            select(InventoryCostLayer)
            .where(*scope, InventoryCostLayer.company_product_id.in_(products), open_or_target)
            .order_by(
                InventoryCostLayer.company_product_id,
                InventoryCostLayer.received_at,
                InventoryCostLayer.id,
            )
            .with_for_update()
        ).all()
        for model in locked:
            layer = _layer(model)
            self._layers[layer.id] = layer
            self._product_of[layer.id] = model.company_product_id
            self._loaded_remaining[layer.id] = layer.remaining
            # La capa bloqueada sustituye a la leída sin bloqueo (mismo estado: su saldo está bloqueado).
            if self._latest.get(model.company_product_id) is not None and self._latest[model.company_product_id].id == layer.id:
                self._latest[model.company_product_id] = layer

    def check_entry_reversals(self, lines: Sequence[Any]) -> None:
        """`ENTRY_LAYER_CONSUMED` antes que el saldo insuficiente (Historia 3, escenario 6; FR-053).

        Con valoración, el saldo de un producto es la suma de sus capas abiertas: si la
        capa de la entrada sigue completa, el saldo siempre alcanza para retirarla. Por
        eso una entrada consumida se rechaza con su causa precisa y no con
        `INSUFFICIENT_STOCK`.
        """
        needed: dict[UUID, Decimal] = {}
        for line in lines:
            if line.movement_type != MOVEMENT_ENTRY_REVERSAL:
                continue
            entry_id = self._entry_layer_of.get(line.reversed_movement_id)
            if entry_id is not None:
                layer = self._layers.get(entry_id)
                if layer is None or layer.remaining != layer.original or layer.original != line.quantity:
                    raise EntryLayerConsumedError()
                continue
            opening_id = self._opening_of.get(line.company_product_id)
            opening = self._layers.get(opening_id) if opening_id else None
            needed[opening_id] = needed.get(opening_id, Decimal(0)) + line.quantity
            if opening is None or opening.remaining < needed[opening_id]:
                raise EntryLayerConsumedError()

    def _product_layers(self, product: UUID) -> list[Layer]:
        return [layer for layer_id, layer in self._layers.items() if self._product_of[layer_id] == product]

    # 3. Valoración por línea -----------------------------------------------------------

    def value_line(self, row: dict[str, Any], line: Any, *, origin_id: UUID) -> list[dict[str, str]]:
        """Completa `unit_cost`, `movement_value` y `cost_known` del movimiento; devuelve errores `422`."""
        movement_type = row["movement_type"]
        product = row["company_product_id"]
        quantity = row["quantity"]

        if movement_type in (PURCHASE_ENTRY, POSITIVE_ADJUSTMENT):
            field = line.cost_field or f"lines[{line.index}].unit_cost"
            if movement_type == PURCHASE_ENTRY:
                if line.unit_cost is None:
                    return [field_error(field, "UNIT_COST_REQUIRED", "El costo unitario es obligatorio.")]
                cost = line.unit_cost
            else:
                candidates = self._product_layers(product)
                latest = self._latest.get(product)
                if latest is not None and latest.id not in self._layers:
                    candidates.append(latest)
                try:
                    cost = positive_adjustment_cost(candidates, line.unit_cost)
                except UnitCostRequired:
                    return [
                        field_error(
                            field,
                            "UNIT_COST_REQUIRED",
                            "No hay un costo conocido para el producto en la sucursal: informe el costo unitario.",
                        )
                    ]
            if line_value(quantity, cost) >= MAX_MONEY:
                return [_value_out_of_range(line)]
            if self._currency_code is None:
                raise RuntimeError("Falta la moneda de la empresa para crear la capa de costo")
            self._create_layer(row, line, cost, origin_id=origin_id)
            row.update(unit_cost=cost, movement_value=line_value(quantity, cost), cost_known=True)
            return []

        if movement_type in (SALE_OUTPUT, NEGATIVE_ADJUSTMENT):
            try:
                takes = consume(self._product_layers(product), quantity)
            except LayersExhausted as error:
                raise ValuationInvariantError(str(error)) from None
            self._record(row, CONSUME, [(take, None) for take in takes])
            return [_value_out_of_range(line)] if row["movement_value"] >= MAX_MONEY else []

        if movement_type == MOVEMENT_OUTPUT_REVERSAL:
            originals = self._originals.get(line.reversed_movement_id, [])
            try:
                restores = restore(self._layers, [original.take for original in originals])
            except OutputNotValued:
                raise OutputNotValuedError() from None
            except LayersExhausted as error:
                raise ValuationInvariantError(str(error)) from None
            self._record(
                row, RESTORE, [(take, original.consumption_id) for take, original in zip(restores, originals, strict=True)]
            )
            return []

        if movement_type == MOVEMENT_ENTRY_REVERSAL:
            entry_id = self._entry_layer_of.get(line.reversed_movement_id)
            opening_id = self._opening_of.get(product)
            try:
                take = reverse_entry(
                    self._layers.get(entry_id) if entry_id else None,
                    self._layers.get(opening_id) if opening_id and entry_id is None else None,
                    quantity,
                )
            except EntryLayerConsumed:
                raise EntryLayerConsumedError() from None
            self._record(row, ENTRY_REVERSAL, [(take, None)])
            # El reverso de una entrada informa el costo de su capa (Fase A: copia el costo de la entrada),
            # no un costo recalculado desde el valor redondeado.
            row["unit_cost"] = take.unit_cost
            return []

        raise ValueError(f"Tipo de movimiento sin valoración: {movement_type}")

    def _create_layer(self, row: dict[str, Any], line: Any, cost: Decimal, *, origin_id: UUID) -> None:
        # Capas de una misma operación: el orden FIFO respeta el orden de sus líneas.
        layer = Layer(
            id=uuid4(),
            kind=ENTRY if row["movement_type"] == PURCHASE_ENTRY else ADJUSTMENT,
            original=row["quantity"],
            remaining=row["quantity"],
            unit_cost=cost,
            cost_known=True,
            received_at=self._now + timedelta(microseconds=line.index),
        )
        self._layers[layer.id] = layer
        self._product_of[layer.id] = row["company_product_id"]
        is_entry = row["movement_type"] == PURCHASE_ENTRY
        self._new_layers.append(
            _NewLayer(
                layer=layer,
                company_product_id=row["company_product_id"],
                origin_movement_id=row["id"],
                origin_purchase_id=origin_id if is_entry else None,
                origin_purchase_detail_id=row["origin_detail_id"] if is_entry else None,
            )
        )
        self._latest[row["company_product_id"]] = layer

    def _record(self, row: dict[str, Any], kind: str, takes: Iterable[tuple[Take, UUID | None]]) -> None:
        takes = list(takes)
        value = sum((take.cost_amount for take, _ in takes), Decimal("0.00"))
        for take, restores_id in takes:
            self._consumptions.append(
                {
                    "id": uuid4(),
                    "movement_id": row["id"],
                    "cost_layer_id": take.layer_id,
                    "consumption_type": kind,
                    "restores_consumption_id": restores_id,
                    "quantity": take.quantity,
                    "unit_cost": take.unit_cost,
                    "cost_known": take.cost_known,
                    "cost_amount": take.cost_amount,
                    "created_at": self._now,
                    "created_by": self._actor,
                }
            )
        row.update(
            movement_value=value,
            unit_cost=output_unit_cost(value, row["quantity"]),
            cost_known=all(take.cost_known for take, _ in takes),
        )

    # 4. Invariante RC-15 ----------------------------------------------------------------

    def settle(self, quantities: dict[UUID, Decimal]) -> dict[UUID, Valuation]:
        """Valoración de cada saldo; `ValuationInvariantError` si Σ capas abiertas ≠ saldo."""
        result: dict[UUID, Valuation] = {}
        for product, quantity in quantities.items():
            current = valuation(self._product_layers(product))
            if current.quantity != quantity or any(
                layer.remaining < 0 or layer.remaining > layer.original for layer in self._product_layers(product)
            ):
                raise ValuationInvariantError(
                    f"Capas abiertas {current.quantity} ≠ saldo {quantity} del producto {product}"
                )
            result[product] = current
        return result

    # 5. Escritura -----------------------------------------------------------------------

    def persist(self) -> None:
        session = self._session
        if self._new_layers:
            session.execute(
                insert(InventoryCostLayer),
                [
                    {
                        "id": item.layer.id,
                        "company_id": self._company_id,
                        "branch_id": self._branch_id,
                        "company_product_id": item.company_product_id,
                        "layer_kind": item.layer.kind,
                        "origin_movement_id": item.origin_movement_id,
                        "origin_purchase_id": item.origin_purchase_id,
                        "origin_purchase_detail_id": item.origin_purchase_detail_id,
                        "original_quantity": item.layer.original,
                        "remaining_quantity": item.layer.remaining,
                        "unit_cost": item.layer.unit_cost,
                        "cost_known": True,
                        "currency_code": self._currency_code,
                        "received_at": item.layer.received_at,
                        "status": item.layer.status,
                        "created_at": self._now,
                        "created_by": self._actor,
                        "updated_at": self._now,
                        "updated_by": self._actor,
                    }
                    for item in self._new_layers
                ],
            )

        changed = [
            {"layer_id": layer_id, "remaining": layer.remaining, "status": layer.status}
            for layer_id, layer in self._layers.items()
            if layer_id in self._loaded_remaining and layer.remaining != self._loaded_remaining[layer_id]
        ]
        if changed:
            session.connection().execute(
                update(InventoryCostLayer.__table__)
                .where(InventoryCostLayer.__table__.c.id == bindparam("layer_id"))
                .values(
                    remaining_quantity=bindparam("remaining"),
                    status=bindparam("status"),
                    updated_at=self._now,
                    updated_by=self._actor,
                ),
                changed,
            )

        if self._consumptions:
            # Las restituciones referencian consumos ya existentes: un solo `INSERT` basta.
            session.execute(insert(InventoryCostConsumption), self._consumptions)


# ----------------------------------------------------------------------------------
# Consultas
# ----------------------------------------------------------------------------------

VALUATION_AT = text(
    """
    SELECT l.unit_cost, l.cost_known,
           l.original_quantity - COALESCE(
               SUM(CASE WHEN c.consumption_type = 'RESTORE' THEN -c.quantity ELSE c.quantity END)
                   FILTER (WHERE m.balance_sequence <= :sequence), 0
           ) AS remaining
    FROM inventory_cost_layers l
    LEFT JOIN inventory_movements om ON om.id = l.origin_movement_id
    LEFT JOIN inventory_cost_consumptions c ON c.cost_layer_id = l.id
    LEFT JOIN inventory_movements m ON m.id = c.movement_id
    WHERE l.company_id = :company AND l.branch_id = :branch AND l.company_product_id = :product
      AND (l.origin_movement_id IS NULL OR om.balance_sequence <= :sequence)
    GROUP BY l.id, l.unit_cost, l.cost_known, l.original_quantity
    """
)


def valuation_at(session: Session, company: UUID, branch: UUID, product: UUID, sequence: int) -> Valuation:
    """Valoración del saldo tal como quedó tras el movimiento `sequence` (respuesta de un reintento)."""
    rows = session.execute(
        VALUATION_AT, {"company": company, "branch": branch, "product": product, "sequence": sequence}
    ).all()
    epoch = datetime.min
    return valuation(
        Layer(uuid4(), OPENING, row.remaining, row.remaining, row.unit_cost, row.cost_known, epoch) for row in rows
    )


@dataclass(frozen=True, slots=True)
class BranchValuationRow:
    company_product_id: UUID
    quantity: Decimal
    inventory_value: Decimal
    average_unit_cost: Decimal | None
    has_unknown_cost: bool
    open_layers: int


@dataclass(frozen=True, slots=True)
class BranchValuation:
    items: list[BranchValuationRow]
    total_records: int
    total_value: Decimal
    has_unknown_cost: bool


@dataclass(frozen=True, slots=True)
class LayerRow:
    id: UUID
    layer_kind: str
    origin_movement_id: UUID | None
    original_quantity: Decimal
    remaining_quantity: Decimal
    unit_cost: Decimal
    cost_known: bool
    currency_code: str | None
    received_at: datetime
    status: str


@dataclass(frozen=True, slots=True)
class ConsumptionRow:
    id: UUID
    cost_layer_id: UUID
    consumption_type: str
    quantity: Decimal
    unit_cost: Decimal
    cost_amount: Decimal
    cost_known: bool
    restores_consumption_id: UUID | None


BRANCH_VALUATION = text(
    """
    SELECT b.company_product_id, b.quantity, b.inventory_value, b.average_unit_cost, b.has_unknown_cost,
           (SELECT count(*) FROM inventory_cost_layers l
             WHERE l.company_id = b.company_id AND l.branch_id = b.branch_id
               AND l.company_product_id = b.company_product_id AND l.status = 'OPEN') AS open_layers
    FROM inventory_balances b
    WHERE b.company_id = :company AND b.branch_id = :branch AND b.quantity > 0
    ORDER BY b.company_product_id
    OFFSET :offset LIMIT :limit
    """
)

BRANCH_TOTALS = text(
    """
    SELECT count(*) AS total_records,
           COALESCE(sum(inventory_value), 0) AS total_value,
           COALESCE(bool_or(has_unknown_cost), false) AS has_unknown_cost
    FROM inventory_balances
    WHERE company_id = :company AND branch_id = :branch AND quantity > 0
    """
)


class SqlValuationQueries:
    """Consultas de valoración (rutas 29–31); siempre filtradas por empresa y sucursal en SQL (RC-06)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def branch_valuation(self, company_id: UUID, branch_id: UUID, *, page: int, page_size: int) -> BranchValuation:
        params = {"company": company_id, "branch": branch_id}
        try:
            totals = self._session.execute(BRANCH_TOTALS, params).one()
            rows = self._session.execute(
                BRANCH_VALUATION, {**params, "offset": (page - 1) * page_size, "limit": page_size}
            ).all()
            return BranchValuation(
                items=[BranchValuationRow(*row) for row in rows],
                total_records=totals.total_records,
                total_value=Decimal(totals.total_value),
                has_unknown_cost=totals.has_unknown_cost,
            )
        finally:
            self._session.rollback()

    def layers(
        self, company_id: UUID, branch_id: UUID, product_id: UUID, *, include_closed: bool, page: int, page_size: int
    ) -> tuple[list[LayerRow], int]:
        conditions = [
            InventoryCostLayer.company_id == company_id,
            InventoryCostLayer.branch_id == branch_id,
            InventoryCostLayer.company_product_id == product_id,
        ]
        if not include_closed:
            conditions.append(InventoryCostLayer.status == "OPEN")
        try:
            total = self._session.scalar(select(func.count()).select_from(InventoryCostLayer).where(*conditions))
            models = self._session.scalars(
                select(InventoryCostLayer)
                .where(*conditions)
                .order_by(InventoryCostLayer.received_at, InventoryCostLayer.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return [LayerRow(**{name: getattr(m, name) for name in LayerRow.__dataclass_fields__}) for m in models], total or 0
        finally:
            self._session.rollback()

    def consumptions(self, company_id: UUID, movement_id: UUID) -> list[ConsumptionRow] | None:
        """Consumos del movimiento; `None` si el movimiento no existe en la empresa."""
        try:
            exists = self._session.scalar(
                select(InventoryMovement.id).where(
                    InventoryMovement.id == movement_id, InventoryMovement.company_id == company_id
                )
            )
            if exists is None:
                return None
            models = self._session.scalars(
                select(InventoryCostConsumption)
                .join(InventoryCostLayer, InventoryCostLayer.id == InventoryCostConsumption.cost_layer_id)
                .where(InventoryCostConsumption.movement_id == movement_id)
                .order_by(InventoryCostLayer.received_at, InventoryCostLayer.id)
            ).all()
            return [ConsumptionRow(**{name: getattr(m, name) for name in ConsumptionRow.__dataclass_fields__}) for m in models]
        finally:
            self._session.rollback()
