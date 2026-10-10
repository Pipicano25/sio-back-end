"""Valores esperados del recorrido calculados por la suite (research R-07; data-model §3.2–§3.4).

Un simulador FIFO mínimo aplica el plan de compras, ventas y anulaciones de `data-model.md` y da saldos,
valores, capas, consumos, costos, márgenes y kardex esperados. Los valores no se leen del sistema: se
comparan con lo que devuelven Inventory y Sales.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

D = Decimal
CENT = D("0.01")


@dataclass
class Layer:
    name: str
    product: str
    original: Decimal
    remaining: Decimal
    unit_cost: Decimal
    origin: str
    removed: bool = False


@dataclass(frozen=True)
class Consumption:
    layer: str
    quantity: Decimal
    unit_cost: Decimal

    @property
    def amount(self) -> Decimal:
        return self.quantity * self.unit_cost


@dataclass(frozen=True)
class Entry:
    reference: str
    product: str
    quantity: Decimal
    unit_cost: Decimal
    layer: str


@dataclass(frozen=True)
class Output:
    reference: str
    product: str
    quantity: Decimal
    revenue: Decimal
    consumptions: tuple[Consumption, ...]

    @property
    def cost(self) -> Decimal:
        return sum((item.amount for item in self.consumptions), D("0"))

    @property
    def margin(self) -> Decimal:
        return self.revenue - self.cost

    @property
    def margin_percent(self) -> Decimal:
        return (self.margin / self.revenue * 100).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Snapshot:
    _layers: tuple[Layer, ...]

    def layers(self, product: str) -> list[Layer]:
        return [layer for layer in self._layers if layer.product == product and not layer.removed]

    def quantity(self, product: str) -> Decimal:
        return sum((layer.remaining for layer in self.layers(product)), D("0"))

    def value(self, product: str) -> Decimal:
        return sum((layer.remaining * layer.unit_cost for layer in self.layers(product)), D("0"))


@dataclass
class Ledger:
    layers: list[Layer] = field(default_factory=list)
    entries: dict[tuple[str, str], Entry] = field(default_factory=dict)
    outputs: dict[str, Output] = field(default_factory=dict)
    movements: list[tuple[str, str, Decimal, str]] = field(default_factory=list)  # producto, tipo, cantidad, origen
    snapshots: dict[str, Snapshot] = field(default_factory=dict)
    reversed_entries: set[str] = field(default_factory=set)

    def entry(self, reference: str, product: str, quantity: str, unit_cost: str, layer: str, factor: str = "1") -> None:
        base_quantity = D(quantity) * D(factor)
        base_cost = D(unit_cost) / D(factor)
        self.layers.append(Layer(layer, product, base_quantity, base_quantity, base_cost, reference))
        self.entries[(reference, product)] = Entry(reference, product, base_quantity, base_cost, layer)
        self.movements.append((product, "PURCHASE_ENTRY", base_quantity, reference))

    def output(self, reference: str, product: str, quantity: str, revenue: str) -> None:
        pending = D(quantity)
        consumptions = []
        for layer in self.layers:
            if layer.product != product or layer.removed or layer.remaining <= 0 or pending <= 0:
                continue
            taken = min(layer.remaining, pending)
            layer.remaining -= taken
            pending -= taken
            consumptions.append(Consumption(layer.name, taken, layer.unit_cost))
        if pending > 0:
            raise ValueError(f"{reference}: existencias insuficientes de {product}")
        self.outputs[reference] = Output(reference, product, D(quantity), D(revenue), tuple(consumptions))
        self.movements.append((product, "SALE_OUTPUT", -D(quantity), reference))

    def reverse_output(self, reference: str) -> None:
        output = self.outputs[reference]
        by_name = {layer.name: layer for layer in self.layers}
        for item in output.consumptions:
            by_name[item.layer].remaining += item.quantity
        self.movements.append((output.product, "OUTPUT_REVERSAL", output.quantity, reference))

    def can_reverse_entry(self, reference: str) -> bool:
        layers = [layer for layer in self.layers if layer.origin == reference and not layer.removed]
        return bool(layers) and all(layer.remaining == layer.original for layer in layers)

    def reverse_entry(self, reference: str) -> None:
        if not self.can_reverse_entry(reference):
            raise ValueError(f"{reference}: capa consumida (ENTRY_LAYER_CONSUMED)")
        for layer in self.layers:
            if layer.origin == reference and not layer.removed:
                layer.removed = True
                layer.remaining = D("0")
                self.movements.append((layer.product, "ENTRY_REVERSAL", -layer.original, reference))
        self.reversed_entries.add(reference)

    def snapshot(self, name: str) -> None:
        self.snapshots[name] = Snapshot(tuple(Layer(**vars(layer)) for layer in self.layers))


@dataclass
class Plan:
    ledger: Ledger

    def snapshot(self, name: str) -> Snapshot:
        return self.ledger.snapshots[name]

    def entry(self, reference: str, product: str) -> Entry:
        return self.ledger.entries[(reference, product)]

    def output(self, reference: str) -> Output:
        return self.ledger.outputs[reference]

    def can_reverse_entry(self, reference: str) -> bool:
        return self.ledger.can_reverse_entry(reference)

    def entry_reversed(self, reference: str) -> bool:
        return reference in self.ledger.reversed_entries

    def kardex(self, product: str) -> list[tuple[str, Decimal, str]]:
        return [(kind, quantity, origin) for item_product, kind, quantity, origin in self.ledger.movements if item_product == product]

    def running_balances(self, product: str) -> list[Decimal]:
        balance, result = D("0"), []
        for _, quantity, _ in self.kardex(product):
            balance += quantity
            result.append(balance)
        return result


def mvp_plan() -> Plan:
    """Plan de data-model.md §3: P1–P3, V1–V3, anulación de V3 y P3 (P1 no se puede anular)."""
    ledger = Ledger()
    ledger.entry("P1", "A", "2", "12000", "L1", factor="12")
    ledger.entry("P1", "B", "10", "5000", "LB")
    ledger.entry("P2", "A", "26", "1200", "L2")
    ledger.entry("P3", "A", "5", "1300", "L3")
    ledger.snapshot("compras")
    ledger.output("V1", "A", "12", "16000")
    ledger.output("V2", "A", "20", "30000")
    ledger.output("V3", "B", "4", "28000")
    ledger.snapshot("ventas")
    ledger.reverse_output("V3")
    ledger.reverse_entry("P3")
    ledger.snapshot("final")
    return Plan(ledger)


def money(value: Decimal) -> str:
    """Formato de montos en las respuestas (2 decimales)."""
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def quantity(value: Decimal) -> str:
    """Formato de cantidades y costos unitarios en las respuestas (4 decimales)."""
    return str(value.quantize(D("0.0001"), rounding=ROUND_HALF_UP))
