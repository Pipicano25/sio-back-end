"""Margen bruto de una línea (FR-019, DS-06, P-01, C-03; research.md R-10).

- Solo con `cost_known = true`: `neto = subtotal − descuento`; `monto = neto − cost_total`
  (puede ser negativo; impuestos excluidos).
- Porcentaje = `ROUND_HALF_UP(monto / neto × 100, 4)`.
- **P-01**: el porcentaje queda `None` si el neto es 0 (no definido) o si el valor no puede
  representarse en `NUMERIC(7,4)` (`|valor| ≥ 1000`). Nunca se satura, trunca ni inventa.
- `cost_known = false` → monto y porcentaje `None`.

`outcome` distingue el motivo de un porcentaje nulo para pruebas, log y evidencia sin
persistirlo (es derivable de `cost_known` y del neto guardados).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sales_service.domain.money import MONEY_QUANTUM, QUANTITY_QUANTUM

COMPUTED = "COMPUTED"
NET_ZERO = "NET_ZERO"
OUT_OF_RANGE = "OUT_OF_RANGE"
COST_UNKNOWN = "COST_UNKNOWN"
MARGIN_OUTCOMES = (COMPUTED, NET_ZERO, OUT_OF_RANGE, COST_UNKNOWN)

PERCENTAGE_LIMIT = Decimal("1000")
"""`NUMERIC(7,4)` representa hasta ±999.9999."""


@dataclass(frozen=True, slots=True)
class MarginResult:
    amount: Decimal | None
    percentage: Decimal | None
    outcome: str


def compute_margin(
    subtotal: Decimal, discount_amount: Decimal, cost_total: Decimal, cost_known: bool
) -> MarginResult:
    if not cost_known:
        return MarginResult(None, None, COST_UNKNOWN)

    net = subtotal - discount_amount
    amount = (net - cost_total).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    if net == 0:
        return MarginResult(amount, None, NET_ZERO)

    percentage = (amount / net * 100).quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)
    if abs(percentage) >= PERCENTAGE_LIMIT:
        return MarginResult(amount, None, OUT_OF_RANGE)
    return MarginResult(amount, percentage, COMPUTED)
