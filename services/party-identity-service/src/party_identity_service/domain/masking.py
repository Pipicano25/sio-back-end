"""Enmascaramiento de datos sensibles (DS-09, FR-054).

Se usa en logs, mensajes de error y cualquier contexto donde no se necesite el
valor completo. Las respuestas de consulta autorizadas devuelven el dato real.
"""

from datetime import date

VISIBLE_SUFFIX = 4
MASK_CHAR = "*"
MASKED_BIRTH_DATE = "****-**-**"


def mask_identification_number(value: str | None) -> str | None:
    """Enmascara un número de identificación conservando sus últimos 4 caracteres.

    Args:
        value: Número de identificación.

    Returns:
        Número enmascarado (`******7890`), todo enmascarado si tiene 4
        caracteres o menos, o `None` si no se informó.
    """
    if value is None:
        return None

    if len(value) <= VISIBLE_SUFFIX:
        return MASK_CHAR * len(value)

    hidden = len(value) - VISIBLE_SUFFIX

    return MASK_CHAR * hidden + value[hidden:]


def mask_birth_date(value: date | str | None) -> str | None:
    """Enmascara una fecha de nacimiento.

    Args:
        value: Fecha de nacimiento.

    Returns:
        `****-**-**` o `None` si no se informó.
    """
    if value is None:
        return None

    return MASKED_BIRTH_DATE
