"""Existencias por producto, equivalencias y estado frente al mínimo (FR-022-41, FR-022-42, FR-022-50). Funciones puras.

- Las cantidades van siempre en la unidad base del producto, con 4 decimales; nunca se repiten por presentación
  (RC-022-5).
- `balance_state`: `REGISTERED` si Inventory tiene el saldo (aunque sea 0), `NOT_REGISTERED` si no.
- Equivalencias: `whole_units` es la parte entera de `total / factor` y `remainder_base_quantity` lo que sobra en
  unidad base (120 tabletas con cajas de 10 → 12 cajas y resto 0).
- `minimum_state`: `NO_POLICY` sin política activa; `BELOW_MINIMUM` solo si la cantidad es estrictamente menor que
  el mínimo. Con mínimo 0 nunca hay alerta, porque el saldo nunca es negativo.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from uuid import UUID

from product_inventory_query_service.application.ports import Balance, Policy

QUANTUM = Decimal("0.0001")
ZERO = Decimal("0")


def fmt(value: Decimal) -> str:
    return format(value.quantize(QUANTUM), "f")


@dataclass(frozen=True, slots=True)
class BranchStock:
    branch_id: UUID
    base_quantity: Decimal
    balance_state: str
    minimum_stock: Decimal | None = None
    minimum_state: str | None = None


@dataclass(frozen=True, slots=True)
class Equivalence:
    company_product_presentation_id: UUID
    whole_units: int
    remainder_base_quantity: Decimal


def branch_stock(branch_id: UUID, balance: Balance | None, policy: Policy | None, *, with_minimums: bool) -> BranchStock:
    quantity = balance.quantity if balance is not None else ZERO
    state = "REGISTERED" if balance is not None and balance.registered else "NOT_REGISTERED"
    if not with_minimums:
        return BranchStock(branch_id, quantity, state)
    minimum = policy.minimum_stock if policy is not None else None
    return BranchStock(branch_id, quantity, state, minimum, minimum_state(quantity, minimum))


def minimum_state(quantity: Decimal, minimum: Decimal | None) -> str:
    if minimum is None:
        return "NO_POLICY"
    if quantity < minimum:
        return "BELOW_MINIMUM"
    if quantity == minimum:
        return "AT_MINIMUM"
    return "ABOVE_MINIMUM"


def total_quantity(branches: list[BranchStock]) -> Decimal:
    return sum((branch.base_quantity for branch in branches), ZERO)


def stock_state(total: Decimal) -> str:
    return "IN_STOCK" if total > 0 else "OUT_OF_STOCK"


def equivalence(presentation_id: UUID, total: Decimal, factor: Decimal) -> Equivalence:
    if factor <= 0:
        raise ValueError("El factor de la presentación debe ser mayor que cero.")
    whole = (total / factor).to_integral_value(rounding=ROUND_DOWN)
    return Equivalence(presentation_id, int(whole), total - whole * factor)


def shortfall(quantity: Decimal, minimum: Decimal) -> Decimal:
    return minimum - quantity
