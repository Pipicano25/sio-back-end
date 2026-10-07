"""Hitos logísticos de la compra (FR-035 a FR-038, DS-08; research.md R-10).

- Orden canónico: `ORDERED ≤ SUPPLIER_DISPATCHED ≤ ARRIVED ≤ RECEIVED ≤ AVAILABLE_FOR_SALE`.
- Un tipo puede registrarse varias veces; el **vigente** es el último registrado
  (`created_at`, `id`). Un registro nuevo se valida contra los vigentes de los demás tipos.
- `occurred_at` no puede ser futuro (tolerancia de 5 minutos).
- `RECEIVED` y `AVAILABLE_FOR_SALE` solo en compras `CONFIRMED`; ninguno en `CANCELLED`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from purchase_service.domain.status import CANCELLED, CONFIRMED, DRAFT

ORDERED = "ORDERED"
SUPPLIER_DISPATCHED = "SUPPLIER_DISPATCHED"
ARRIVED = "ARRIVED"
RECEIVED = "RECEIVED"
AVAILABLE_FOR_SALE = "AVAILABLE_FOR_SALE"
EVENT_ORDER = (ORDERED, SUPPLIER_DISPATCHED, ARRIVED, RECEIVED, AVAILABLE_FOR_SALE)
SOURCES = ("USER", "SUPPLIER", "INTEGRATION", "SYSTEM")
FUTURE_TOLERANCE = timedelta(minutes=5)

ALLOWED_STATUSES = {
    ORDERED: (DRAFT, CONFIRMED),
    SUPPLIER_DISPATCHED: (DRAFT, CONFIRMED),
    ARRIVED: (DRAFT, CONFIRMED),
    RECEIVED: (CONFIRMED,),
    AVAILABLE_FOR_SALE: (CONFIRMED,),
}


class EventNotAllowedError(Exception):
    """El hito no se permite en el estado de la compra (`409`)."""


class EventOrderError(ValueError):
    """`occurred_at` incoherente con otro hito vigente (`422 EVENT_OUT_OF_ORDER`)."""

    def __init__(self, conflicting_type: str, conflicting_id: UUID) -> None:
        super().__init__(conflicting_type)
        self.conflicting_type = conflicting_type
        self.conflicting_id = conflicting_id


class EventInFutureError(ValueError):
    """`occurred_at` posterior a ahora más la tolerancia (`422 EVENT_IN_FUTURE`)."""


@dataclass(frozen=True, slots=True)
class EventRecord:
    id: UUID
    event_type: str
    occurred_at: datetime
    created_at: datetime


def current_events(events: Iterable[EventRecord]) -> dict[str, EventRecord]:
    """Hito vigente por tipo: el último por `(created_at, id)`."""
    current: dict[str, EventRecord] = {}

    for event in events:
        previous = current.get(event.event_type)
        if previous is None or (event.created_at, str(event.id)) > (previous.created_at, str(previous.id)):
            current[event.event_type] = event

    return current


def check_new_event(
    status: str, event_type: str, occurred_at: datetime, existing: Sequence[EventRecord], now: datetime
) -> None:
    """Valida un hito nuevo; lanza la excepción correspondiente si no es admisible."""
    if status == CANCELLED or status not in ALLOWED_STATUSES[event_type]:
        raise EventNotAllowedError(event_type)

    if occurred_at > now + FUTURE_TOLERANCE:
        raise EventInFutureError(event_type)

    position = EVENT_ORDER.index(event_type)

    for other_type, other in current_events(existing).items():
        if other_type == event_type:
            continue
        other_position = EVENT_ORDER.index(other_type)
        if other_position < position and other.occurred_at > occurred_at:
            raise EventOrderError(other_type, other.id)
        if other_position > position and other.occurred_at < occurred_at:
            raise EventOrderError(other_type, other.id)


def _hours(start: datetime, end: datetime) -> Decimal:
    return (Decimal((end - start).total_seconds()) / Decimal(3600)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class Interval:
    from_type: str
    to_type: str
    hours: Decimal


def intervals(events: Iterable[EventRecord]) -> tuple[list[Interval], Decimal | None]:
    """Intervalos entre hitos vigentes consecutivos y lead time total `ORDERED → AVAILABLE_FOR_SALE`."""
    current = current_events(events)
    present = [event_type for event_type in EVENT_ORDER if event_type in current]
    result = [
        Interval(start, end, _hours(current[start].occurred_at, current[end].occurred_at))
        for start, end in zip(present, present[1:], strict=False)
    ]
    total = (
        _hours(current[ORDERED].occurred_at, current[AVAILABLE_FOR_SALE].occurred_at)
        if ORDERED in current and AVAILABLE_FOR_SALE in current
        else None
    )
    return result, total
