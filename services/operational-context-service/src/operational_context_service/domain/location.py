"""Reglas puras de ubicación: jerarquía geográfica local y coordenadas (R-07, R-08)."""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from operational_context_service.domain.errors import (
    DomainValidationError,
    GeographyParentRequiredError,
)

MAX_COORDINATE_DECIMALS = 6
LATITUDE_RANGE = (Decimal("-90"), Decimal("90"))
LONGITUDE_RANGE = (Decimal("-180"), Decimal("180"))


def check_hierarchy(
    country_id: UUID | None,
    administrative_division_id: UUID | None,
    city_id: UUID | None,
) -> None:
    """Exige el país cuando se informa división o ciudad (FR-031).

    No consulta Geography: la coherencia entre niveles se valida después con
    los datos del proveedor.

    Raises:
        GeographyParentRequiredError: Si hay división o ciudad sin país.
    """
    if country_id is not None:
        return

    if administrative_division_id is not None:
        raise GeographyParentRequiredError(field="country_id")

    if city_id is not None:
        raise GeographyParentRequiredError(field="country_id")


def normalize_coordinate(
    value: Decimal | float | int | str | None,
    *,
    field: str,
) -> Decimal | None:
    """Convierte una coordenada a `Decimal` sin redondear (máximo 6 decimales).

    Raises:
        DomainValidationError: Si no es numérica, es infinita o tiene más de
            6 decimales.
    """
    if value is None:
        return None

    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DomainValidationError(
            "La coordenada debe ser un número decimal.",
            field=field,
        ) from None

    if not number.is_finite():
        raise DomainValidationError("La coordenada debe ser finita.", field=field)

    exponent = number.as_tuple().exponent

    if isinstance(exponent, int) and exponent < -MAX_COORDINATE_DECIMALS:
        raise DomainValidationError(
            f"La coordenada admite como máximo {MAX_COORDINATE_DECIMALS} decimales; "
            "no se redondea.",
            field=field,
        )

    return number


def validate_coordinates(
    latitude: Decimal | None,
    longitude: Decimal | None,
) -> None:
    """Valida la pareja y los rangos de las coordenadas (FR-034).

    Raises:
        DomainValidationError: Si falta una de las dos o está fuera de rango.
    """
    if (latitude is None) != (longitude is None):
        missing = "longitude" if longitude is None else "latitude"
        raise DomainValidationError(
            "La latitud y la longitud deben informarse juntas.",
            field=missing,
        )

    if latitude is not None and not LATITUDE_RANGE[0] <= latitude <= LATITUDE_RANGE[1]:
        raise DomainValidationError(
            "La latitud debe estar entre -90 y 90.",
            field="latitude",
        )

    if longitude is not None and not LONGITUDE_RANGE[0] <= longitude <= LONGITUDE_RANGE[1]:
        raise DomainValidationError(
            "La longitud debe estar entre -180 y 180.",
            field="longitude",
        )
