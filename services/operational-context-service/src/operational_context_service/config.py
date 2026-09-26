"""Configuración propia de Operational Context Service."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Settings:
    """Representa la configuración del microservicio.

    La configuración no selecciona comportamientos funcionales distintos por
    entorno: Party Identity y Geography se consumen siempre con el mismo
    contrato (FR-040, R-12).

    Attributes:
        docs_enabled: Indica si Swagger y OpenAPI están habilitados.
        database_url: URL de conexión hacia PostgreSQL.
        party_identity_base_url: URL base de Party Identity Service, con `/api/v1`.
        party_identity_timeout_seconds: Tiempo de espera de cada llamada.
        geography_base_url: URL base de Geography Service, con su prefijo vigente.
        geography_timeout_seconds: Tiempo de espera de cada llamada.
        keycloak_base_url: URL base de Keycloak para el token técnico y la Admin
            API de solo lectura (R-06, R-16).
        keycloak_client_id: Cliente técnico propio del servicio (DS-14).
        keycloak_client_secret: Secreto del cliente técnico; nunca se registra.
        keycloak_realm: Realm de SIO.
        keycloak_timeout_seconds: Tiempo de espera de cada llamada a Keycloak.
        sio_api_client_id: Cliente cuyos roles son los permisos SIO.
    """

    docs_enabled: bool
    database_url: str
    party_identity_base_url: str
    geography_base_url: str
    keycloak_base_url: str
    keycloak_client_id: str
    keycloak_client_secret: str = field(repr=False)
    party_identity_timeout_seconds: float = 5.0
    geography_timeout_seconds: float = 5.0
    keycloak_realm: str = "sio"
    keycloak_timeout_seconds: float = 5.0
    sio_api_client_id: str = "sio-api"


def load_settings() -> Settings:
    """Carga la configuración del servicio desde variables de entorno.

    Raises:
        RuntimeError: Si una variable contiene un valor inválido.
    """
    return Settings(
        docs_enabled=_read_bool("SIO_DOCS_ENABLED", default=False),
        database_url=_required_text("DATABASE_URL"),
        party_identity_base_url=_read_text(
            "PARTY_IDENTITY_SERVICE_BASE_URL",
            default="http://localhost:8002/api/v1",
        ),
        party_identity_timeout_seconds=_read_positive_float(
            "PARTY_IDENTITY_TIMEOUT_SECONDS",
            default=5.0,
        ),
        geography_base_url=_read_text(
            "GEOGRAPHY_SERVICE_BASE_URL",
            default="http://localhost:8000",
        ),
        geography_timeout_seconds=_read_positive_float(
            "GEOGRAPHY_TIMEOUT_SECONDS",
            default=5.0,
        ),
        keycloak_base_url=_required_text("KEYCLOAK_BASE_URL").rstrip("/"),
        keycloak_realm=_read_text("KEYCLOAK_REALM", default="sio"),
        keycloak_client_id=_required_text("OPERATIONAL_CONTEXT_CLIENT_ID"),
        keycloak_client_secret=_required_text("OPERATIONAL_CONTEXT_CLIENT_SECRET"),
        keycloak_timeout_seconds=_read_positive_float(
            "KEYCLOAK_TIMEOUT_SECONDS",
            default=5.0,
        ),
        sio_api_client_id=_read_text("SIO_API_CLIENT_ID", default="sio-api"),
    )


def _read_optional_text(name: str) -> str | None:
    value = os.getenv(name)

    if value is None or not value.strip():
        return None

    return value.strip()


def _required_text(name: str) -> str:
    value = _read_optional_text(name)

    if value is None:
        raise RuntimeError(
            f"La variable de entorno {name} es obligatoria y no puede estar vacía."
        )

    return value


def _read_text(name: str, default: str) -> str:
    value = _read_optional_text(name)

    return (value or default).rstrip("/")


def _read_positive_float(name: str, default: float) -> float:
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


def _read_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()

    if normalized in {"true", "1", "yes", "on"}:
        return True

    if normalized in {"false", "0", "no", "off"}:
        return False

    raise RuntimeError(
        f"La variable de entorno {name} debe contener un valor booleano válido."
    )
