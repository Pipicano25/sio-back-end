"""Normalización de códigos, nombres e identificadores (FR-003, FR-004, R-08, R-17)."""

from __future__ import annotations

import re
import unicodedata

from product_catalog_service.application.exceptions import ValidationError

_SPACES = re.compile(r"\s+")
_IDENTIFIER_NOISE = re.compile(r"[\s-]+")


def normalize_code(value: str, *, max_length: int, field: str = "code") -> str:
    """Quita espacios extremos y pasa a mayúsculas; rechaza vacío o exceso de longitud."""
    normalized = (value or "").strip().upper()

    if not normalized:
        raise ValidationError("El código no puede estar vacío.", field=field)

    if len(normalized) > max_length:
        raise ValidationError(
            f"El código no puede superar {max_length} caracteres.",
            field=field,
        )

    return normalized


def normalize_name(value: str, *, max_length: int, field: str = "name") -> str:
    """Quita espacios extremos y colapsa los internos; exige un valor significativo."""
    normalized = _SPACES.sub(" ", (value or "").strip())

    if not normalized:
        raise ValidationError("El nombre no puede estar vacío.", field=field)

    if len(normalized) > max_length:
        raise ValidationError(
            f"El nombre no puede superar {max_length} caracteres.",
            field=field,
        )

    return normalized


def normalize_optional_text(value: str | None) -> str | None:
    """Devuelve el texto sin espacios extremos o `None` si queda vacío."""
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def canonical_name_key(value: str) -> str:
    """Clave de búsqueda: minúsculas, sin tildes y con espacios colapsados (máx. 200)."""
    decomposed = unicodedata.normalize("NFKD", value or "")
    without_marks = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return _SPACES.sub(" ", without_marks.strip().lower())[:200]


def normalize_identifier_value(value: str) -> str:
    """Quita espacios y guiones de un identificador; nunca lo interpreta como número."""
    normalized = _IDENTIFIER_NOISE.sub("", value or "")

    if not normalized:
        raise ValidationError("El identificador no puede estar vacío.", field="value")

    if len(normalized) > 100:
        raise ValidationError(
            "El identificador no puede superar 100 caracteres.",
            field="value",
        )

    return normalized
