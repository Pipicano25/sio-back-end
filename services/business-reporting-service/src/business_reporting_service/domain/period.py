"""Período de un reporte (spec 023, DR-02 y DR-09; FR-023-50).

- `date_from` y `date_to` son fechas de negocio, ambas incluidas; el período tiene como máximo 366 días.
- `date_to` no puede ser posterior a hoy en la zona horaria de la empresa.
- Para Inventory (movimientos con `TIMESTAMPTZ`), el período de una sucursal es el intervalo `[from, to)` entre la
  medianoche de `date_from` y la de `date_to + 1` en la zona de la sucursal.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from business_reporting_service.application.exceptions import ValidationFailedError


@dataclass(frozen=True, slots=True)
class Period:
    date_from: date
    date_to: date

    @property
    def days(self) -> int:
        return (self.date_to - self.date_from).days + 1

    def instants(self, timezone: str) -> tuple[datetime, datetime]:
        """`[from, to)` de la sucursal: medianoche de `date_from` y de `date_to + 1` en su zona horaria."""
        zone = zone_of(timezone)
        start = datetime.combine(self.date_from, time.min, tzinfo=zone)
        end = datetime.combine(self.date_to + timedelta(days=1), time.min, tzinfo=zone)
        return start, end


def zone_of(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValidationFailedError(
            "La zona horaria de la empresa o la sucursal no es válida.",
            errors=[{"field": "timezone", "message": "Zona horaria desconocida.", "code": "INVALID_TIMEZONE"}],
        ) from None


def build_period(date_from: date, date_to: date, *, today: date, max_days: int) -> Period:
    """Valida el período; todo error es `422` con el campo y un código estable."""
    errors = []
    if date_to < date_from:
        errors.append({"field": "date_to", "message": "La fecha final no puede ser anterior a la inicial.",
                       "code": "INVALID_DATE_RANGE"})
    elif (date_to - date_from).days + 1 > max_days:
        errors.append({"field": "date_to", "message": f"El período no puede superar {max_days} días.",
                       "code": "PERIOD_TOO_LONG"})
    if date_to > today:
        errors.append({"field": "date_to", "message": "La fecha final no puede ser posterior a hoy.",
                       "code": "DATE_IN_FUTURE"})
    if errors:
        raise ValidationFailedError("La solicitud contiene parámetros inválidos.", errors=errors)
    return Period(date_from, date_to)


def today_in(timezone: str, now: datetime) -> date:
    return now.astimezone(zone_of(timezone)).date()
