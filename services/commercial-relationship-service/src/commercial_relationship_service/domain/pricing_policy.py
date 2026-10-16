"""Reglas de las políticas de precios de lista (spec 021: FR-021-01..04).

- El recargo va de 0 a 1.000 % inclusive, con hasta 4 decimales; no se redondea (se rechaza).
- `INACTIVE` es final: una política inactiva no se reactiva ni se modifica.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from commercial_relationship_service.domain.errors import MarkupPercentageOutOfRangeError

MARKUP_FIELD = "markup_percentage"
MAX_MARKUP = Decimal(1000)
MARKUP_PLACES = 4
MAX_PRESENTATIONS_PER_REQUEST = 100


def validate_markup(value: object) -> Decimal:
    """Devuelve el recargo como `Decimal` exacto.

    Raises:
        MarkupPercentageOutOfRangeError: Si no es un número, es negativo, supera 1.000 o tiene más de 4 decimales.
    """
    if isinstance(value, bool):
        raise MarkupPercentageOutOfRangeError(field=MARKUP_FIELD)
    try:
        markup = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise MarkupPercentageOutOfRangeError(field=MARKUP_FIELD) from None
    if not markup.is_finite() or markup < 0 or markup > MAX_MARKUP:
        raise MarkupPercentageOutOfRangeError(field=MARKUP_FIELD)
    exponent = markup.normalize().as_tuple().exponent
    if isinstance(exponent, int) and -exponent > MARKUP_PLACES:
        raise MarkupPercentageOutOfRangeError(field=MARKUP_FIELD)
    return markup


def unique_in_order(ids: list) -> list:
    """Identificadores sin repetir, conservando el orden en que se enviaron."""
    return list(dict.fromkeys(ids))
