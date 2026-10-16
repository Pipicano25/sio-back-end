"""Tasa de impuesto de compra del producto de la empresa (spec 021: FR-021-07, M-3).

`None` significa **sin configurar** y es distinto de `0`, que es una tasa válida. Una tasa configurada no vuelve a
"sin configurar". El rango es de 0 a 100 % con hasta 4 decimales; no se redondea (se rechaza).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from commercial_relationship_service.domain.errors import (
    PurchaseTaxRequiredError,
    TaxPercentageOutOfRangeError,
)

TAX_FIELD = "purchase_tax_percentage"
MAX_TAX = Decimal(100)
TAX_PLACES = 4


def validate_purchase_tax(value: object, *, field: str = TAX_FIELD) -> Decimal:
    """Devuelve la tasa como `Decimal` exacto.

    Raises:
        PurchaseTaxRequiredError: Si es `None`.
        TaxPercentageOutOfRangeError: Si no es un número de 0 a 100 con hasta 4 decimales.
    """
    if value is None:
        raise PurchaseTaxRequiredError(field=field)
    if isinstance(value, bool):
        raise TaxPercentageOutOfRangeError(field=field)
    try:
        tax = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise TaxPercentageOutOfRangeError(field=field) from None
    if not tax.is_finite() or tax < 0 or tax > MAX_TAX:
        raise TaxPercentageOutOfRangeError(field=field)
    exponent = tax.normalize().as_tuple().exponent
    if isinstance(exponent, int) and -exponent > TAX_PLACES:
        raise TaxPercentageOutOfRangeError(field=field)
    return tax
