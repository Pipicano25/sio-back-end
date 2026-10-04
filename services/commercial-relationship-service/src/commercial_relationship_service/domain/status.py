"""Estados y transiciones explícitas (FR-016, FR-025, FR-033, "Ciclo de vida y estados").

El `PUT` nunca cambia el estado (DS-17); solo estas acciones lo hacen.
"""

from __future__ import annotations

from commercial_relationship_service.domain.errors import InvalidStatusTransitionError

ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
BLOCKED = "BLOCKED"

DEACTIVATE = "deactivate"
REACTIVATE = "reactivate"
BLOCK = "block"
UNBLOCK = "unblock"

# Productos empresariales y clientes: ACTIVE <-> INACTIVE.
_SIMPLE_TRANSITIONS = {
    DEACTIVATE: ({ACTIVE}, INACTIVE),
    REACTIVATE: ({INACTIVE}, ACTIVE),
}

# Proveedores: además BLOCKED, del que solo se sale desbloqueando.
_SUPPLIER_TRANSITIONS = {
    DEACTIVATE: ({ACTIVE}, INACTIVE),
    REACTIVATE: ({INACTIVE}, ACTIVE),
    BLOCK: ({ACTIVE, INACTIVE}, BLOCKED),
    UNBLOCK: ({BLOCKED}, ACTIVE),
}


def next_status(current: str, action: str, *, supplier: bool = False) -> str:
    """Estado destino de una acción, o `INVALID_STATUS_TRANSITION` si no se permite.

    Raises:
        InvalidStatusTransitionError: Si la acción no es válida desde `current`.
    """
    table = _SUPPLIER_TRANSITIONS if supplier else _SIMPLE_TRANSITIONS
    allowed_from, target = table.get(action, (set(), None))

    if current not in allowed_from or target is None:
        raise InvalidStatusTransitionError(
            f"La acción {action} no es válida desde el estado {current}."
        )

    return target
