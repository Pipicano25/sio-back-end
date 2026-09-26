"""Validación de zonas horarias IANA (FR-012, R-08).

Se consulta exclusivamente la base IANA del paquete `tzdata`, para que el
resultado sea idéntico en Windows, en la imagen `python:3.13-slim` y en las
pruebas, sin depender de la base del sistema operativo.
"""

from importlib import resources

from operational_context_service.domain.errors import DomainValidationError

DEFAULT_TIMEZONE = "America/Bogota"
MAX_TIMEZONE_LENGTH = 60


def is_valid_timezone(value: str) -> bool:
    """Indica si `value` es un identificador IANA presente en `tzdata`."""
    if not value or len(value) > MAX_TIMEZONE_LENGTH:
        return False

    parts = value.split("/")

    if any(
        not part or part.startswith(".") or "\\" in part or ":" in part
        for part in parts
    ):
        return False

    try:
        return resources.files("tzdata.zoneinfo").joinpath(*parts).is_file()
    except (ModuleNotFoundError, OSError, ValueError):
        return False


def normalize_timezone(value: str, *, field: str = "timezone") -> str:
    """Recorta y valida una zona horaria IANA.

    Raises:
        DomainValidationError: Si no es un identificador IANA válido.
    """
    candidate = value.strip() if isinstance(value, str) else ""

    if not is_valid_timezone(candidate):
        raise DomainValidationError(
            "La zona horaria debe ser un identificador IANA válido "
            "(por ejemplo, America/Bogota).",
            field=field,
        )

    return candidate
