"""Configuración propia de Commercial Relationship Service (research R-16)."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Settings:
    """Representa la configuración del microservicio.

    La configuración no selecciona comportamientos funcionales distintos por
    entorno: Operational Context, Product Catalog y Party Identity se consumen
    siempre con el mismo contrato y un único adaptador real (FR-050).

    Attributes:
        docs_enabled: Indica si Swagger y OpenAPI están habilitados.
        database_url: URL de conexión hacia PostgreSQL.
        operational_context_base_url: URL base de Operational Context, con `/api/v1`.
        product_catalog_base_url: URL base de Product Catalog, con `/api/v1`.
        party_identity_base_url: URL base de Party Identity, con `/api/v1`.
        payment_reference_base_url: URL base de Payment Reference, **sin** `/api/v1`
            (el proveedor aún no publica el prefijo, GAP-PR-14; C-06 de la 010).
        keycloak_base_url: URL base de Keycloak para el token técnico (R-05).
        keycloak_client_id: Cliente técnico propio del servicio.
        keycloak_client_secret: Secreto del cliente técnico; nunca se registra.
        keycloak_realm: Realm de SIO.
        *_timeout_seconds: Tiempo de espera de cada llamada saliente.
    """

    docs_enabled: bool
    database_url: str
    operational_context_base_url: str
    product_catalog_base_url: str
    party_identity_base_url: str
    keycloak_base_url: str
    keycloak_client_id: str
    keycloak_client_secret: str = field(repr=False)
    payment_reference_base_url: str = "http://localhost:8105"
    operational_context_timeout_seconds: float = 5.0
    product_catalog_timeout_seconds: float = 5.0
    party_identity_timeout_seconds: float = 5.0
    payment_reference_timeout_seconds: float = 5.0
    keycloak_realm: str = "sio"
    keycloak_timeout_seconds: float = 5.0


def load_settings() -> Settings:
    """Carga la configuración del servicio desde variables de entorno.

    Raises:
        RuntimeError: Si una variable contiene un valor inválido.
    """
    return Settings(
        docs_enabled=_read_bool("SIO_DOCS_ENABLED", default=False),
        database_url=_required_text("DATABASE_URL"),
        operational_context_base_url=_read_text(
            "OPERATIONAL_CONTEXT_SERVICE_BASE_URL",
            default="http://localhost:8004/api/v1",
        ),
        operational_context_timeout_seconds=_read_positive_float(
            "OPERATIONAL_CONTEXT_TIMEOUT_SECONDS",
            default=5.0,
        ),
        product_catalog_base_url=_read_text(
            "PRODUCT_CATALOG_SERVICE_BASE_URL",
            default="http://localhost:8003/api/v1",
        ),
        product_catalog_timeout_seconds=_read_positive_float(
            "PRODUCT_CATALOG_TIMEOUT_SECONDS",
            default=5.0,
        ),
        party_identity_base_url=_read_text(
            "PARTY_IDENTITY_SERVICE_BASE_URL",
            default="http://localhost:8002/api/v1",
        ),
        party_identity_timeout_seconds=_read_positive_float(
            "PARTY_IDENTITY_TIMEOUT_SECONDS",
            default=5.0,
        ),
        payment_reference_base_url=_read_text(
            "PAYMENT_REFERENCE_SERVICE_BASE_URL",
            default="http://localhost:8105",
        ),
        payment_reference_timeout_seconds=_read_positive_float(
            "PAYMENT_REFERENCE_TIMEOUT_SECONDS",
            default=5.0,
        ),
        keycloak_base_url=_required_text("KEYCLOAK_BASE_URL").rstrip("/"),
        keycloak_realm=_read_text("KEYCLOAK_REALM", default="sio"),
        keycloak_client_id=_required_text("COMMERCIAL_RELATIONSHIP_CLIENT_ID"),
        keycloak_client_secret=_required_text("COMMERCIAL_RELATIONSHIP_CLIENT_SECRET"),
        keycloak_timeout_seconds=_read_positive_float(
            "KEYCLOAK_TIMEOUT_SECONDS",
            default=5.0,
        ),
    )



@dataclass(frozen=True, slots=True)
class PriceWorkerSettings:
    """Configuración del `commercial-relationship-price-worker` (spec 021).

    El worker solo usa la base propia: no hace llamadas HTTP ni necesita credenciales técnicas.

    Attributes:
        database_url: URL de conexión hacia PostgreSQL; nunca se registra.
        interval_seconds: Espera entre ciclos.
        batch_size: Aplicaciones procesadas como máximo por ciclo.
        max_backoff_seconds: Tope de la espera creciente entre reintentos de una aplicación.
    """

    database_url: str = field(repr=False)
    interval_seconds: float = 5.0
    batch_size: int = 50
    max_backoff_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.batch_size < 1:
            raise RuntimeError("CR_PRICE_WORKER_BATCH_SIZE debe ser al menos 1.")
        if self.max_backoff_seconds < self.interval_seconds:
            raise RuntimeError(
                "CR_PRICE_WORKER_MAX_BACKOFF_SECONDS debe ser al menos CR_PRICE_WORKER_INTERVAL_SECONDS."
            )


def load_price_worker_settings() -> PriceWorkerSettings:
    """Carga la configuración del worker de precios desde variables de entorno.

    Raises:
        RuntimeError: Si una variable falta o contiene un valor inválido.
    """
    return PriceWorkerSettings(
        database_url=_required_text("DATABASE_URL"),
        interval_seconds=_read_positive_float("CR_PRICE_WORKER_INTERVAL_SECONDS", 5.0),
        batch_size=int(_read_positive_float("CR_PRICE_WORKER_BATCH_SIZE", 50)),
        max_backoff_seconds=_read_positive_float("CR_PRICE_WORKER_MAX_BACKOFF_SECONDS", 300.0),
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
