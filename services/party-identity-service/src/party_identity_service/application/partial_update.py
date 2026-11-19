"""Actualización parcial y versión opcional (constitución 4.0.0: Principio VII, D9, D10 y D28).

`UNSET` marca un campo que el cliente no envió: no cambia.
"""

from __future__ import annotations

from typing import Any, Final


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

