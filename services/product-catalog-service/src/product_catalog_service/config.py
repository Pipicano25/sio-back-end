"""Configuración propia de Product Catalog Service."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Representa la configuración del microservicio.

    Attributes:
        docs_enabled: Indica si Swagger y OpenAPI están habilitados.
        database_url: URL de conexión hacia PostgreSQL.
        party_identity_service_base_url: URL base de Party Identity Service,
            incluido su prefijo de ruta.
        party_identity_timeout_seconds: Tiempo de espera de la validación del
            fabricante.
    """

    docs_enabled: bool
    database_url: str
    party_identity_service_base_url: str
    party_identity_timeout_seconds: float


def load_settings() -> Settings:
    """Carga la configuración del servicio desde variables de entorno.

    Returns:
        Configuración obtenida desde el entorno.

    Raises:
        RuntimeError: Si una variable obligatoria falta o tiene un valor inválido.
    """
    return Settings(
        docs_enabled=_read_bool(
            name="SIO_DOCS_ENABLED",
            default=False,
        ),
        database_url=_required_text("DATABASE_URL"),
        party_identity_service_base_url=_read_text(
            name="PARTY_IDENTITY_SERVICE_BASE_URL",
            default="http://localhost:8002",
        ),
        party_identity_timeout_seconds=_read_float(
            name="PARTY_IDENTITY_TIMEOUT_SECONDS",
            default=3.0,
        ),
    )


def _required_text(name: str) -> str:
    """Obtiene una variable de entorno de texto obligatoria."""
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"La variable de entorno {name} es obligatoria y no puede estar vacía."
        )

    return value.strip()


def _read_text(
    name: str,
    default: str,
) -> str:
    """Obtiene una variable opcional de texto sin barra final."""
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    return value.strip().rstrip("/")


def _read_float(
    name: str,
    default: float,
) -> float:
    """Obtiene una variable opcional numérica mayor que cero."""
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        number = float(value.strip())
    except ValueError as exc:
        raise RuntimeError(
            f"La variable de entorno {name} debe ser un número."
        ) from exc

    if number <= 0:
        raise RuntimeError(
            f"La variable de entorno {name} debe ser mayor que cero."
        )

    return number


def _read_bool(name: str, default: bool) -> bool:
    """Obtiene una variable de entorno booleana."""
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()

    if normalized_value in {"true", "1", "yes", "on"}:
        return True

    if normalized_value in {"false", "0", "no", "off"}:
        return False

    raise RuntimeError(
        f"La variable de entorno {name} debe contener un valor booleano válido."
    )
