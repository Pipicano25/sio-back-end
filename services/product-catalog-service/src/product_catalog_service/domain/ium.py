"""Identificador Único de Medicamento (IUM) del INVIMA (spec 018, FR-056b, DS-01)."""

from __future__ import annotations

import re

IUM_TYPE = "IUM"
# Forma oficial observada en el CUM del INVIMA (99,4 % de los valores): 1 dígito, 1 letra y 13 dígitos.
IUM_PATTERN = r"^[0-9][A-Z][0-9]{13}$"
_IUM = re.compile(IUM_PATTERN)


def is_valid_ium(value: str) -> bool:
    """Indica si el valor normalizado tiene la forma del IUM (sin cambiar mayúsculas)."""
    return bool(_IUM.fullmatch(value))
