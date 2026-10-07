"""Valoración FIFO pura (research.md R-03; FR-050 a FR-057; DS-15 a DS-17; RC-14, RC-15; T005)."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from uuid import UUID, uuid4

import pytest

from inventory_service.domain.fifo import (
    ADJUSTMENT,
    ENTRY,
    OPENING,
    EntryLayerConsumed,
    Layer,
    LayersExhausted,
    OutputNotValued,
    UnitCostRequired,
    consume,
    fifo_order,
    positive_adjustment_cost,
    restore,
    reverse_entry,
    valuation,
)

T0 = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


def layer(quantity, cost, *, kind=ENTRY, at=0, remaining=None, known=True, layer_id: UUID | None = None) -> Layer:
    q = D(str(quantity))
    return Layer(
        id=layer_id or uuid4(),
        kind=kind,
        original=q,
        remaining=q if remaining is None else D(str(remaining)),
        unit_cost=D(str(cost)),
        cost_known=known,
        received_at=T0 + timedelta(seconds=at),
    )


def test_consume_takes_oldest_layers_first_and_closes_exhausted_ones() -> None:
    old, new = layer(10, 1000, at=1), layer(5, 1300, at=2)
    takes = consume([new, old], D("12"))
    assert [(t.layer_id, t.quantity, t.unit_cost, t.cost_amount) for t in takes] == [
        (old.id, D("10"), D("1000"), D("10000.00")),
        (new.id, D("2"), D("1300"), D("2600.00")),
    ]
    assert (old.remaining, old.status, new.remaining, new.status) == (D("0"), "CLOSED", D("3"), "OPEN")
    assert valuation([old, new]).value == D("3900.00")


def test_fifo_order_breaks_ties_by_id() -> None:
    a = layer(1, 1, layer_id=UUID(int=2))
    b = layer(1, 2, layer_id=UUID(int=1))
    assert fifo_order([a, b]) == [b, a]


def test_consume_skips_closed_layers() -> None:
    closed = layer(4, 1, at=1, remaining=0)
    open_ = layer(4, 2, at=2)
    takes = consume([closed, open_], D("1"))
    assert [t.layer_id for t in takes] == [open_.id]


def test_consume_more_than_open_layers_fails() -> None:
    with pytest.raises(LayersExhausted):
        consume([layer(2, 1)], D("3"))


def test_restore_returns_quantities_to_the_same_layers_with_the_same_cost() -> None:
    old, new = layer(10, 1000, at=1), layer(5, 1300, at=2)
    takes = consume([old, new], D("12"))
    restores = restore({old.id: old, new.id: new}, takes)
    assert [(r.layer_id, r.quantity, r.unit_cost, r.cost_amount) for r in restores] == [
        (t.layer_id, t.quantity, t.unit_cost, t.cost_amount) for t in takes
    ]
    assert (old.remaining, old.status, new.remaining) == (D("10"), "OPEN", D("5"))
    assert valuation([old, new]).value == D("16500.00")


def test_restore_without_consumptions_is_output_not_valued() -> None:
    with pytest.raises(OutputNotValued):
        restore({}, [])


def test_entry_reversal_with_intact_layer_retires_it_completely() -> None:
    entry = layer(10, 1000)
    take = reverse_entry(entry, None, D("10"))
    assert (take.layer_id, take.quantity, take.cost_amount) == (entry.id, D("10"), D("10000.00"))
    assert (entry.remaining, entry.status) == (D("0"), "CLOSED")


@pytest.mark.parametrize("remaining", ["9.9999", "5", "0"])
def test_entry_reversal_with_consumed_layer_is_rejected_without_changes(remaining) -> None:
    entry = layer(10, 1000, remaining=remaining)
    with pytest.raises(EntryLayerConsumed):
        reverse_entry(entry, None, D("10"))
    assert entry.remaining == D(remaining)


def test_pre_valuation_entry_reversal_uses_the_opening_layer() -> None:
    opening = layer(20, 800, kind=OPENING, known=False)
    take = reverse_entry(None, opening, D("15"))
    assert (take.layer_id, take.quantity, take.unit_cost, take.cost_known) == (opening.id, D("15"), D("800"), False)
    assert opening.remaining == D("5")
    with pytest.raises(EntryLayerConsumed):
        reverse_entry(None, opening, D("6"))
    assert opening.remaining == D("5")
    with pytest.raises(EntryLayerConsumed):
        reverse_entry(None, None, D("1"))


def test_positive_adjustment_cost_rule() -> None:
    older = layer(5, 900, at=1, remaining=0)
    latest_closed = layer(5, 1100, kind=ADJUSTMENT, at=3, remaining=0)
    middle = layer(5, 1000, at=2)
    # La capa más reciente, abierta o cerrada.
    assert positive_adjustment_cost([older, latest_closed, middle], None) == D("1100")
    # Un costo informado se usa en su lugar.
    assert positive_adjustment_cost([older, middle], D("1234.5")) == D("1234.5")
    # Sin capas: costo obligatorio.
    with pytest.raises(UnitCostRequired):
        positive_adjustment_cost([], None)
    assert positive_adjustment_cost([], D("0")) == D("0")
    # La más reciente es una apertura sin costo: no hay costo conocido (FR-052, FR-063).
    unknown = layer(5, 0, kind=OPENING, at=4, known=False)
    with pytest.raises(UnitCostRequired):
        positive_adjustment_cost([middle, unknown], None)
    assert positive_adjustment_cost([middle, unknown], D("700")) == D("700")


def test_cost_known_propagates_to_takes_and_valuation() -> None:
    unknown = layer(3, 0, kind=OPENING, at=1, known=False)
    known = layer(3, 10, at=2)
    takes = consume([unknown, known], D("4"))
    assert [t.cost_known for t in takes] == [False, True]
    assert valuation([unknown, known]).has_unknown_cost is False  # la apertura quedó agotada
    assert valuation([layer(1, 0, kind=OPENING, known=False)]).has_unknown_cost is True


def test_valuation_average_and_quantity() -> None:
    result = valuation([layer(1, "0.3333"), layer(2, "0.3333"), layer(4, 1, remaining=0)])
    # 1 × 0.3333 → 0.33 y 2 × 0.3333 → 0.67: cada capa se redondea por separado.
    assert (result.quantity, result.value, result.average_unit_cost) == (D("3"), D("1.00"), D("0.3333"))
    assert valuation([]).average_unit_cost is None


@pytest.mark.parametrize("seed", range(500))
def test_random_sequences_keep_layers_equal_to_balance(seed: int) -> None:
    """Propiedad RC-14/RC-15: Σ restante = saldo y 0 ≤ restante ≤ original tras cada paso."""
    rng = random.Random(seed)
    layers: list[Layer] = []
    balance = D(0)
    outputs: list[list] = []
    entries: list[Layer] = []
    clock = 0

    for _ in range(40):
        action = rng.choice(["entry", "entry", "output", "output", "restore", "reverse_entry"])
        if action == "entry":
            clock += 1
            new = layer(D(rng.randint(1, 50)) / 4, D(rng.randint(0, 9999)) / 100, at=clock)
            layers.append(new)
            entries.append(new)
            balance += new.original
        elif action == "output" and balance > 0:
            quantity = min(balance, D(rng.randint(1, 60)) / 4)
            takes = consume(layers, quantity)
            assert sum(t.quantity for t in takes) == quantity
            outputs.append(takes)
            balance -= quantity
        elif action == "restore" and outputs:
            takes = outputs.pop(rng.randrange(len(outputs)))
            restore({item.id: item for item in layers}, takes)
            balance += sum(t.quantity for t in takes)
        elif action == "reverse_entry" and entries:
            target = entries[rng.randrange(len(entries))]
            try:
                reverse_entry(target, None, target.original)
            except EntryLayerConsumed:
                assert target.remaining != target.original
            else:
                entries.remove(target)
                balance -= target.original

        assert sum(item.remaining for item in layers) == balance
        assert all(D(0) <= item.remaining <= item.original for item in layers)
        assert valuation(layers).quantity == balance
