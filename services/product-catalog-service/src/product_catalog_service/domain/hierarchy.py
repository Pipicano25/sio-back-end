"""Reglas de jerarquía para categorías y grupos (RC-02, FR-021, FR-063)."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

MAX_DEPTH_GUARD = 10_000


def would_create_cycle(
    node_id: UUID,
    new_parent_id: UUID | None,
    parent_of: Callable[[UUID], UUID | None],
) -> bool:
    """Indica si asignar `new_parent_id` como padre de `node_id` crea un ciclo.

    Recorre los ancestros del nuevo padre; hay ciclo si aparece el propio nodo
    (incluida la autorreferencia).
    """
    current = new_parent_id
    steps = 0

    while current is not None:
        if current == node_id:
            return True

        steps += 1
        if steps > MAX_DEPTH_GUARD:
            # Datos corruptos: una cadena de ancestros infinita ya es un ciclo.
            return True

        current = parent_of(current)

    return False
