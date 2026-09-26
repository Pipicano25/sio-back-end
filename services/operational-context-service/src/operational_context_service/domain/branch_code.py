"""Código interno de sucursal (FR-021)."""

from operational_context_service.domain.errors import DomainValidationError

MAX_CODE_LENGTH = 40


def normalize_code(value: str, *, field: str = "code") -> str:
    """Recorta espacios exteriores y pasa a mayúsculas; 1–40 caracteres.

    Raises:
        DomainValidationError: Si queda vacío o supera 40 caracteres.
    """
    candidate = value.strip().upper() if isinstance(value, str) else ""

    if not candidate:
        raise DomainValidationError("El código de la sucursal es obligatorio.", field=field)

    if len(candidate) > MAX_CODE_LENGTH:
        raise DomainValidationError(
            f"El código de la sucursal admite como máximo {MAX_CODE_LENGTH} caracteres.",
            field=field,
        )

    return candidate
