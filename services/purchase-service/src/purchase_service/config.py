"""Configuración de Purchase Service (variables de entorno, Principio IX).

No existen modos por entorno: las seis dependencias y Keycloak se consumen siempre
con su adaptador real; las pruebas inyectan dobles por DI en `create_app`
(research.md R-15, R-17).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

RECONCILER_THRESHOLD_FACTOR = 10
"""El umbral del conciliador debe ser al menos 10 veces el tiempo de espera de Inventory (R-08)."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuración del microservicio.

    Las URL incluyen `/api/v1`, salvo Payment Reference (brecha diferida de ese servicio).
    """

    docs_enabled: bool
    database_url: str
    operational_context_base_url: str
    commercial_relationship_base_url: str
    product_catalog_base_url: str
    party_identity_base_url: str
    payment_reference_base_url: str
    inventory_base_url: str
    keycloak_token_url: str
    client_id: str
    client_secret: str
    operational_context_timeout_seconds: float = 5.0
    commercial_relationship_timeout_seconds: float = 5.0
    product_catalog_timeout_seconds: float = 5.0
    party_identity_timeout_seconds: float = 5.0
    payment_reference_timeout_seconds: float = 5.0
    inventory_timeout_seconds: float = 10.0
    lookup_concurrency: int = 8
    lock_timeout_seconds: float = 5.0
    reconciler_interval_seconds: float = 60.0
    reconciler_threshold_seconds: float = 300.0
    price_worker_interval_seconds: float = 5.0
    price_worker_max_backoff_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.reconciler_threshold_seconds < RECONCILER_THRESHOLD_FACTOR * self.inventory_timeout_seconds:
            raise RuntimeError(
                "PURCHASE_RECONCILER_THRESHOLD_SECONDS debe ser al menos "
                f"{RECONCILER_THRESHOLD_FACTOR} veces INVENTORY_TIMEOUT_SECONDS."
            )
        if self.lookup_concurrency < 1:
            raise RuntimeError("PURCHASE_LOOKUP_CONCURRENCY debe ser al menos 1.")
        if self.price_worker_max_backoff_seconds < self.price_worker_interval_seconds:
            raise RuntimeError(
                "PURCHASE_PRICE_WORKER_MAX_BACKOFF_SECONDS debe ser al menos PURCHASE_PRICE_WORKER_INTERVAL_SECONDS."
            )

    def __repr__(self) -> str:  # nunca muestra el secreto ni la URL de la base
        return f"Settings(client_id={self.client_id!r}, docs_enabled={self.docs_enabled!r})"


def load_database_url() -> str:
    """URL de la base propia (la usa también `alembic/env.py`)."""
    return _required_text("DATABASE_URL")


def load_settings() -> Settings:
    """Carga la configuración desde variables de entorno.

    Raises:
        RuntimeError: Si falta una variable obligatoria o tiene un valor inválido.
    """
    return Settings(
        docs_enabled=_read_bool("SIO_DOCS_ENABLED", default=False),
        database_url=load_database_url(),
        operational_context_base_url=_required_text("OPERATIONAL_CONTEXT_SERVICE_BASE_URL"),
        commercial_relationship_base_url=_required_text("COMMERCIAL_RELATIONSHIP_SERVICE_BASE_URL"),
        product_catalog_base_url=_required_text("PRODUCT_CATALOG_SERVICE_BASE_URL"),
        party_identity_base_url=_required_text("PARTY_IDENTITY_SERVICE_BASE_URL"),
        payment_reference_base_url=_required_text("PAYMENT_REFERENCE_SERVICE_BASE_URL"),
        inventory_base_url=_required_text("INVENTORY_SERVICE_BASE_URL"),
        keycloak_token_url=_required_text("KEYCLOAK_TOKEN_URL"),
        client_id=_read_text("PURCHASE_CLIENT_ID", default="purchase-service"),
        client_secret=_required_text("PURCHASE_CLIENT_SECRET"),
        operational_context_timeout_seconds=_read_positive_float("OPERATIONAL_CONTEXT_TIMEOUT_SECONDS", 5.0),
        commercial_relationship_timeout_seconds=_read_positive_float("COMMERCIAL_RELATIONSHIP_TIMEOUT_SECONDS", 5.0),
        product_catalog_timeout_seconds=_read_positive_float("PRODUCT_CATALOG_TIMEOUT_SECONDS", 5.0),
        party_identity_timeout_seconds=_read_positive_float("PARTY_IDENTITY_TIMEOUT_SECONDS", 5.0),
        payment_reference_timeout_seconds=_read_positive_float("PAYMENT_REFERENCE_TIMEOUT_SECONDS", 5.0),
        inventory_timeout_seconds=_read_positive_float("INVENTORY_TIMEOUT_SECONDS", 10.0),
        lookup_concurrency=int(_read_positive_float("PURCHASE_LOOKUP_CONCURRENCY", 8)),
        lock_timeout_seconds=_read_positive_float("PURCHASE_LOCK_TIMEOUT_SECONDS", 5.0),
        reconciler_interval_seconds=_read_positive_float("PURCHASE_RECONCILER_INTERVAL_SECONDS", 60.0),
        reconciler_threshold_seconds=_read_positive_float("PURCHASE_RECONCILER_THRESHOLD_SECONDS", 300.0),
        # Spec 021: entrega de solicitudes de precio a Commercial Relationship (EXC-001).
        price_worker_interval_seconds=_read_positive_float("PURCHASE_PRICE_WORKER_INTERVAL_SECONDS", 5.0),
        price_worker_max_backoff_seconds=_read_positive_float("PURCHASE_PRICE_WORKER_MAX_BACKOFF_SECONDS", 300.0),
    )


def _required_text(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(f"La variable de entorno {name} es obligatoria y no puede estar vacía.")

    return value.strip()


def _read_text(name: str, *, default: str) -> str:
    value = os.getenv(name)
    return default if value is None or not value.strip() else value.strip()


def _read_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    normalized = value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise RuntimeError(f"La variable de entorno {name} debe ser booleana.")


def _read_positive_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        parsed = float(value)
    except ValueError as exc:
        raise RuntimeError(f"La variable de entorno {name} debe ser numérica.") from exc

    if parsed <= 0:
        raise RuntimeError(f"La variable de entorno {name} debe ser mayor que cero.")

    return parsed
