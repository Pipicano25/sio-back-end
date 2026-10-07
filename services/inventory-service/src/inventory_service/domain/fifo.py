"""Valoración FIFO pura: capas y consumos (FR-050 a FR-057; DS-15 a DS-17; research.md R-03).

Estas funciones trabajan sobre el estado en memoria de las capas de **un** saldo
(empresa, sucursal y producto) que el repositorio ya bloqueó; no tocan la base.
Mutan `remaining` de las capas y devuelven los consumos (`Take`) que el
repositorio persiste en la misma transacción.

- Consumir (salida, ajuste negativo): capas abiertas de la más antigua a la más
  reciente por `received_at`, `id`.
- Restituir (reverso de salida): devuelve cada consumo original a su misma capa
  con el mismo costo; sin consumos originales → `OutputNotValued` (DS-17).
- Reverso de entrada: la capa de la entrada debe seguir completa; una entrada
  anterior a la valoración se retira de la capa de apertura (DS-16).
- Costo de un ajuste positivo o sobrante: el informado o, si no, el de la capa más
  reciente con costo conocido (FR-052, FR-063).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from inventory_service.domain.rounding import average_unit_cost, inventory_value, line_value

ENTRY = "ENTRY"
ADJUSTMENT = "ADJUSTMENT"
OPENING = "OPENING"
LAYER_KINDS = (ENTRY, ADJUSTMENT, OPENING)

OPEN = "OPEN"
CLOSED = "CLOSED"

CONSUME = "CONSUME"
RESTORE = "RESTORE"
ENTRY_REVERSAL = "ENTRY_REVERSAL"

ZERO = Decimal(0)


class EntryLayerConsumed(Exception):
    """La capa de la entrada (o la apertura) ya no conserva la cantidad a retirar."""


class OutputNotValued(Exception):
    """La salida no tiene consumos FIFO (anterior a la valoración)."""


class UnitCostRequired(Exception):
    """No hay costo conocido para crear la capa: la solicitud debe traer `unit_cost`."""


class LayersExhausted(Exception):
    """Las capas abiertas no alcanzan para la cantidad pedida (invariante roto)."""


@dataclass(slots=True)
class Layer:
    """Estado de una capa de costo de un saldo bloqueado."""

    id: UUID
    kind: str
    original: Decimal
    remaining: Decimal
    unit_cost: Decimal
    cost_known: bool
    received_at: datetime

    @property
    def status(self) -> str:
        return OPEN if self.remaining > 0 else CLOSED


@dataclass(frozen=True, slots=True)
class Take:
    """Cantidad tomada de (o devuelta a) una capa, con su costo (`inventory_cost_consumptions`)."""

    layer_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    cost_known: bool
    cost_amount: Decimal


@dataclass(frozen=True, slots=True)
class Valuation:
    quantity: Decimal
    value: Decimal
    average_unit_cost: Decimal | None
    has_unknown_cost: bool

    @property
    def inventory_value(self) -> Decimal:
        """Nombre de la columna del saldo (`inventory_value`) para el mismo valor."""
        return self.value


def fifo_order(layers: Iterable[Layer]) -> list[Layer]:
    """Capas en orden FIFO: `received_at` y, a igualdad, `id`."""
    return sorted(layers, key=lambda layer: (layer.received_at, layer.id))


def _take(layer: Layer, quantity: Decimal) -> Take:
    return Take(layer.id, quantity, layer.unit_cost, layer.cost_known, line_value(quantity, layer.unit_cost))


def consume(layers: Sequence[Layer], quantity: Decimal) -> list[Take]:
    """Consume `quantity` de las capas abiertas, de la más antigua a la más reciente."""
    available = sum((layer.remaining for layer in layers if layer.remaining > 0), ZERO)
    if available < quantity:
        raise LayersExhausted(f"Capas abiertas {available} < cantidad {quantity}")

    takes: list[Take] = []
    pending = quantity
    for layer in fifo_order(layer for layer in layers if layer.remaining > 0):
        if pending <= 0:
            break
        taken = min(layer.remaining, pending)
        layer.remaining -= taken
        pending -= taken
        takes.append(_take(layer, taken))
    return takes


def restore(layers: Mapping[UUID, Layer], originals: Sequence[Take]) -> list[Take]:
    """Devuelve cada consumo original a su misma capa con el mismo costo (§9.7)."""
    if not originals:
        raise OutputNotValued()

    restores: list[Take] = []
    for original in originals:
        layer = layers[original.layer_id]
        if layer.remaining + original.quantity > layer.original:
            raise LayersExhausted(f"La capa {layer.id} superaría su cantidad original")
        layer.remaining += original.quantity
        restores.append(
            Take(layer.id, original.quantity, original.unit_cost, original.cost_known, original.cost_amount)
        )
    return restores


def reverse_entry(entry_layer: Layer | None, opening: Layer | None, quantity: Decimal) -> Take:
    """Retira una entrada: su capa completa o, sin capa propia, de la apertura (DS-16)."""
    if entry_layer is not None:
        if entry_layer.remaining != entry_layer.original or entry_layer.original != quantity:
            raise EntryLayerConsumed()
        entry_layer.remaining = ZERO
        return _take(entry_layer, quantity)

    if opening is None or opening.remaining < quantity:
        raise EntryLayerConsumed()
    opening.remaining -= quantity
    return _take(opening, quantity)


def positive_adjustment_cost(layers: Sequence[Layer], requested: Decimal | None) -> Decimal:
    """Costo de la capa de un ajuste positivo o sobrante (FR-052, FR-063).

    Un costo informado se usa siempre. Si no se informa, se toma el de la capa más
    reciente (abierta o cerrada); si no hay capas o la más reciente no tiene costo
    conocido (apertura "sin costo"), el costo es obligatorio.
    """
    if requested is not None:
        return requested
    ordered = fifo_order(layers)
    if not ordered or not ordered[-1].cost_known:
        raise UnitCostRequired()
    return ordered[-1].unit_cost


def valuation(layers: Iterable[Layer]) -> Valuation:
    """Cantidad, valor recalculado, costo promedio y presencia de costo desconocido de un saldo."""
    open_layers = [layer for layer in layers if layer.remaining > 0]
    quantity = sum((layer.remaining for layer in open_layers), ZERO)
    value = inventory_value((layer.remaining, layer.unit_cost) for layer in open_layers)
    return Valuation(
        quantity=quantity,
        value=value,
        average_unit_cost=average_unit_cost(value, quantity),
        has_unknown_cost=any(not layer.cost_known for layer in open_layers),
    )
