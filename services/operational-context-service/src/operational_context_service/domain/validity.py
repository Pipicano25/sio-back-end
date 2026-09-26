"""Reglas puras de vigencia de las asignaciones de asesor (FR-050, FR-054).

`now` es inyectable para las pruebas. Todas las fechas deben tener zona
horaria (el almacenamiento es `TIMESTAMPTZ`).
"""

from __future__ import annotations

from datetime import UTC, datetime

from operational_context_service.domain.errors import OperationalContextError


class InvalidValidityPeriodError(OperationalContextError):
    """Vigencia inválida: fechas futuras o `valid_to <= valid_from`."""

    code = "INVALID_VALIDITY_PERIOD"
    title = "Vigencia inválida"
    default_message = "La vigencia indicada no es válida."


def utc_now() -> datetime:
    """Momento actual con zona horaria."""
    return datetime.now(UTC)


def resolve_start(value: datetime | None, *, now: datetime, field: str) -> datetime:
    """Devuelve el inicio de vigencia: el indicado o `now`; nunca futuro.

    Raises:
        InvalidValidityPeriodError: Si la fecha no tiene zona horaria o es futura.
    """
    start = value or now
    _require_timezone(start, field)

    if start > now:
        raise InvalidValidityPeriodError("La vigencia no puede empezar en el futuro.", field=field)

    return start


def resolve_end(
    value: datetime | None,
    *,
    valid_from: datetime,
    now: datetime,
    field: str,
) -> datetime:
    """Devuelve el fin de vigencia: el indicado o `now`; no futuro y mayor que el inicio.

    Raises:
        InvalidValidityPeriodError: Si no tiene zona horaria, es futuro o no es
            posterior a `valid_from`.
    """
    end = value or now
    _require_timezone(end, field)

    if end > now:
        raise InvalidValidityPeriodError("La vigencia no puede terminar en el futuro.", field=field)

    if end <= valid_from:
        raise InvalidValidityPeriodError(
            "El fin de la vigencia debe ser posterior a su inicio.",
            field=field,
        )

    return end


def _require_timezone(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidValidityPeriodError(
            "La fecha debe incluir zona horaria (ISO 8601 con desplazamiento).",
            field=field,
        )
