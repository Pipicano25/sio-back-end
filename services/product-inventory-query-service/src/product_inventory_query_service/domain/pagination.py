"""Derivación de la página a partir del resultado de la búsqueda (`data-model.md` §2.4; FR-022-63, FR-022-64,
FR-022-136).

| Condición | `items` | `has_next` | Cursor | `partial` |
|---|---|---|---|---|
| al menos `need` válidos | los primeros `page_size` | `true` | `PAGE`, posición del último entregado | `false` |
| conductor agotado | todos los válidos | `false` | ninguno | `false` |
| límite de trabajo sin agotar | todos los válidos | `true` | `SCAN`, posición del último examinado | `true` |
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")
WORK_LIMIT_REACHED = "WORK_LIMIT_REACHED"


@dataclass(frozen=True, slots=True)
class Candidate(Generic[T]):
    key: Any
    position: dict
    data: T = None


@dataclass(frozen=True, slots=True)
class SearchOutcome(Generic[T]):
    valid: list[Candidate[T]]
    exhausted: bool
    limited: bool
    last_examined: dict | None
    examined: int = 0
    batches: int = 0


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: list[Candidate[T]]
    has_next: bool
    cursor_kind: str | None = None
    cursor_position: dict | None = None
    partial: bool = False
    partial_reason: str | None = None
    extra: dict = field(default_factory=dict)


def derive_page(outcome: SearchOutcome[T], page_size: int) -> Page[T]:
    if len(outcome.valid) > page_size:
        items = outcome.valid[:page_size]
        return Page(items, True, "PAGE", items[-1].position)
    if outcome.exhausted:
        return Page(list(outcome.valid), False)
    if outcome.limited:
        return Page(list(outcome.valid), True, "SCAN", outcome.last_examined, True, WORK_LIMIT_REACHED)
    raise AssertionError("la búsqueda terminó sin reunir válidos, sin agotar y sin límite")  # pragma: no cover
