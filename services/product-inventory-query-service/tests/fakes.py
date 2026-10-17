"""Dobles de las dependencias (Principio IV).

Esqueleto de la fase 1 de `tasks.md`: los dobles de OC, CR, PC e Inventory, con contador de
llamadas por operación y argumentos, se completan en T066 junto con los puertos (T067).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class CallLog:
    """Registro de llamadas a los dobles: (operación, argumentos normalizados) → veces."""

    calls: Counter = field(default_factory=Counter)

    def record(self, operation: str, arguments: tuple) -> None:
        self.calls[(operation, arguments)] += 1

    def count(self, operation: str) -> int:
        return sum(times for (name, _), times in self.calls.items() if name == operation)
