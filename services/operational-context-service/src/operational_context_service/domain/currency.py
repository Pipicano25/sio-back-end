"""Moneda principal: solo formato de 3 letras (DS-09)."""

import re

from operational_context_service.domain.errors import DomainValidationError

DEFAULT_CURRENCY = "COP"
_CURRENCY = re.compile(r"^[A-Z]{3}$")


def normalize_currency(value: str, *, field: str = "default_currency") -> str:
    """Recorta, pasa a mayúsculas y exige exactamente 3 letras.

    Raises:
        DomainValidationError: Si no son 3 letras.
    """
    candidate = value.strip().upper() if isinstance(value, str) else ""

    if not _CURRENCY.match(candidate):
        raise DomainValidationError(
            "La moneda debe ser un código de 3 letras (por ejemplo, COP).",
            field=field,
        )

    return candidate
