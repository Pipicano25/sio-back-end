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


# --------------------------------------------------------------------------
# Fase B: datos de contacto y referencias documentales (FR-095, RC-13)
# --------------------------------------------------------------------------

TEXT_VISIBLE_PREFIX = 4
PHONE_VISIBLE_DIGITS = 2


def mask_email(value: str | None) -> str | None:
    """Enmascara un correo conservando su primer carácter y el dominio.

    Returns:
        `a***@dominio` (o `a***` si no tiene `@`), o `None`.
    """
    if value is None:
        return None

    local, separator, domain = value.partition("@")
    first = local[:1]

    return f"{first}***{separator}{domain}" if separator else f"{first}***"


def mask_phone(value: str | None) -> str | None:
    """Enmascara un teléfono conservando solo sus 2 últimos dígitos.

    Returns:
        `**23`, todo enmascarado si tiene 2 dígitos o menos, o `None`.
    """
    if value is None:
        return None

    digits = "".join(character for character in value if character.isdigit())

    if len(digits) <= PHONE_VISIBLE_DIGITS:
        return MASK_CHAR * max(len(digits), 1)

    return MASK_CHAR * 2 + digits[-PHONE_VISIBLE_DIGITS:]


def mask_text(value: str | None) -> str | None:
    """Enmascara un texto libre (dirección, código postal, referencia documental).

    Conserva los 4 primeros caracteres y la longitud total.
    """
    if value is None:
        return None

    if len(value) <= TEXT_VISIBLE_PREFIX:
        return MASK_CHAR * len(value)

    return value[:TEXT_VISIBLE_PREFIX] + MASK_CHAR * (len(value) - TEXT_VISIBLE_PREFIX)
