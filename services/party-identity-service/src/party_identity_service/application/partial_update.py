"""Actualización parcial y versión opcional (constitución 4.0.0: Principio VII, D9, D10 y D28).

- `UNSET` marca un campo que el cliente no envió: no cambia.
- `provided` deja solo los campos enviados.
- `check_version` valida la versión esperada solo cuando el cliente la envía.
"""

from __future__ import annotations

from typing import Any, Final

from party_identity_service.application.exceptions import VersionConflictError


class _Unset:
    """Valor de un campo no enviado en una actualización parcial."""

    _instance: "_Unset | None" = None

    def __new__(cls) -> "_Unset":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: Final[Any] = _Unset()


def provided(values: dict[str, Any]) -> dict[str, Any]:
    """Campos enviados por el cliente (sin los `UNSET`)."""
    return {field: value for field, value in values.items() if value is not UNSET}


def check_version(current_version: int, expected_version: int | None) -> int:
    """Valida la versión esperada si el cliente la envió (D9).

    Returns:
        La versión con la que se escribe: la esperada o, si no se envió, la vigente.

    Raises:
        VersionConflictError: Si se envió y no coincide con la vigente.
    """
    if expected_version is not None and expected_version != current_version:
        raise VersionConflictError
    return current_version
