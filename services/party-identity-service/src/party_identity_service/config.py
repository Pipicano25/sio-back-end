"""Configuración propia de Party Identity Service."""

import os
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Settings:
    """Representa la configuración del microservicio.

    La configuración no selecciona comportamientos funcionales distintos por
    entorno: Geography y Operational Context se consumen siempre con el mismo
    contrato (FR-044, FR-101).

    Attributes:
        docs_enabled: Indica si Swagger y OpenAPI están habilitados.
        database_url: URL de conexión hacia PostgreSQL.
        geography_service_base_url: URL base de Geography Service, incluido
            su prefijo de ruta vigente.
        geography_timeout_seconds: Tiempo de espera de las llamadas a Geography.
        operational_context_service_base_url: URL base de Operational Context
            Service, con su prefijo `/api/v1` (confirmación de perfiles).
        operational_context_timeout_seconds: Tiempo de espera de las llamadas
            a Operational Context.
        keycloak_token_url: Endpoint de tokens de Keycloak (`seed` y consulta
            técnica a Operational Context).
        keycloak_timeout_seconds: Tiempo de espera al pedir el token técnico.
        client_id: Cliente técnico del servicio.
        client_secret: Secreto del cliente técnico.
        seed_country_id: País explícito para el `seed` (modo independiente).
    """

    docs_enabled: bool
    database_url: str
    geography_service_base_url: str
    geography_timeout_seconds: float = 5.0
    operational_context_service_base_url: str = "http://localhost:8004/api/v1"
    operational_context_timeout_seconds: float = 5.0
    keycloak_token_url: str | None = None
    keycloak_timeout_seconds: float = 5.0
    client_id: str | None = None
    client_secret: str | None = None
    seed_country_id: UUID | None = None


def load_settings() -> Settings:
    """Carga la configuración del servicio desde variables de entorno.

    Returns:
        Configuración obtenida desde el entorno.

    Raises:
        RuntimeError: Si una variable contiene un valor inválido.
    """
    return Settings(
        docs_enabled=_read_bool(
            name="SIO_DOCS_ENABLED",
            default=False,
        ),
        database_url=_required_text("DATABASE_URL"),
        geography_service_base_url=_read_text(
            name="GEOGRAPHY_SERVICE_BASE_URL",
            default="http://localhost:8000",
        ),
        geography_timeout_seconds=_read_positive_float(
            name="GEOGRAPHY_TIMEOUT_SECONDS",
            default=5.0,
        ),
        operational_context_service_base_url=_read_text(
            name="OPERATIONAL_CONTEXT_SERVICE_BASE_URL",
            default="http://localhost:8004/api/v1",
        ),
        operational_context_timeout_seconds=_read_positive_float(
            name="OPERATIONAL_CONTEXT_TIMEOUT_SECONDS",
            default=5.0,
        ),
        keycloak_token_url=_read_optional_text("KEYCLOAK_TOKEN_URL"),
        keycloak_timeout_seconds=_read_positive_float(
            name="KEYCLOAK_TIMEOUT_SECONDS",
            default=5.0,
        ),
        client_id=_read_optional_text("PARTY_IDENTITY_CLIENT_ID"),
        client_secret=_read_optional_text("PARTY_IDENTITY_CLIENT_SECRET"),
        seed_country_id=_read_optional_uuid("PARTY_IDENTITY_SEED_COUNTRY_ID"),
    )


def _read_optional_text(name: str) -> str | None:
    """Obtiene una variable de texto opcional; vacía equivale a ausente."""
    value = os.getenv(name)

    if value is None or not value.strip():
        return None

    return value.strip()


def _read_optional_uuid(name: str) -> UUID | None:
    """Obtiene una variable opcional que debe contener un UUID."""
    value = _read_optional_text(name)

    if value is None:
        return None

    try:
        return UUID(value)

    except ValueError:
        raise RuntimeError(
            f"La variable de entorno {name} debe contener un UUID válido."
        ) from None


def _read_positive_float(name: str, default: float) -> float:
    """Obtiene una variable numérica positiva (tiempos de espera)."""
    value = _read_optional_text(name)

    if value is None:
        return default

    try:
        number = float(value)

    except ValueError:
        number = 0.0

    if number <= 0:
        raise RuntimeError(
            f"La variable de entorno {name} debe ser un número positivo."
        )

    return number


def _required_text(name: str) -> str:
    """Obtiene una variable de entorno de texto obligatoria.

    Args:
        name: Nombre de la variable de entorno.

    Returns:
        Valor no vacío de la variable.

    Raises:
        RuntimeError: Si la variable no existe o está vacía.
    """
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
    """Obtiene una variable opcional de texto."""
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    return value.strip().rstrip("/")


def _read_bool(name: str, default: bool) -> bool:
    """Obtiene una variable de entorno booleana.

    Args:
        name: Nombre de la variable de entorno.
        default: Valor utilizado cuando la variable no está definida.

    Returns:
        Valor booleano interpretado.

    Raises:
        RuntimeError: Si el valor no representa un booleano válido.
    """
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
