"""Identidad del precio de una línea y su comparación al confirmar (DS-05, P-02; research.md R-07).

Un precio se identifica por su valor por unidad de venta, la lista y el ítem de lista: si
cualquiera difiere entre lo guardado y lo vigente, la confirmación se rechaza con
`409 PRICES_CHANGED` (un cambio de lista o ítem altera la trazabilidad de §8.2 aunque el
valor coincida). La resolución se repite con la intención original: la lista solo se
envía si el vendedor la pidió (`price_list_requested`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sales_service.domain.money import QUANTITY_QUANTUM


@dataclass(frozen=True, slots=True)
class PriceRef:
    unit_price: Decimal
    price_list_id: UUID | None
    price_list_item_id: UUID | None


def price_changed(stored: PriceRef, current: PriceRef) -> bool:
    return (
        stored.unit_price.quantize(QUANTITY_QUANTUM) != current.unit_price.quantize(QUANTITY_QUANTUM)
        or stored.price_list_id != current.price_list_id
        or stored.price_list_item_id != current.price_list_item_id
    )


def list_to_request(*, price_list_requested: bool, price_list_id: UUID | None) -> UUID | None:
    """Lista que se envía a `applicable-prices/resolve` para repetir la intención original (P-02)."""
    return price_list_id if price_list_requested else None
