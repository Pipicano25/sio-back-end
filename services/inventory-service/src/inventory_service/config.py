"""Configuración de Inventory Service (variables de entorno, Principio IX).

No existen modos por entorno: Operational Context, Commercial Relationship y
Keycloak se consumen siempre con su adaptador real; las pruebas inyectan dobles
por DI en `create_app` (research.md R-14, R-16).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuración del microservicio.

    Attributes:
        docs_enabled: Swagger y OpenAPI habilitados (`SIO_DOCS_ENABLED`).
        database_url: URL de conexión a la base propia.
        operational_context_base_url: URL base de Operational Context, con `/api/v1`.
        operational_context_timeout_seconds: Tiempo de espera de Operational Context.
        commercial_relationship_base_url: URL base de Commercial Relationship, con `/api/v1`.
        commercial_relationship_timeout_seconds: Tiempo de espera de Commercial Relationship.
        keycloak_token_url: Endpoint de tokens del realm (`client_credentials`).
        client_id: Cliente técnico propio (`inventory-service`).
        client_secret: Secreto del cliente técnico (solo en `.env`).
        lock_timeout_seconds: Espera máxima de los bloqueos de saldo (R-04).
    """

    docs_enabled: bool
    database_url: str
    operational_context_base_url: str
    commercial_relationship_base_url: str
    keycloak_token_url: str
    client_id: str
    client_secret: str
    operational_context_timeout_seconds: float = 5.0
    commercial_relationship_timeout_seconds: float = 5.0
    lock_timeout_seconds: float = 5.0

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
        keycloak_token_url=_required_text("KEYCLOAK_TOKEN_URL"),
        client_id=_read_text("INVENTORY_CLIENT_ID", default="inventory-service"),
        client_secret=_required_text("INVENTORY_CLIENT_SECRET"),
        operational_context_timeout_seconds=_read_positive_float(
            "OPERATIONAL_CONTEXT_TIMEOUT_SECONDS", default=5.0
        ),
        commercial_relationship_timeout_seconds=_read_positive_float(
            "COMMERCIAL_RELATIONSHIP_TIMEOUT_SECONDS", default=5.0
        ),
        lock_timeout_seconds=_read_positive_float("INVENTORY_LOCK_TIMEOUT_SECONDS", default=5.0),
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


def _read_positive_float(name: str, *, default: float) -> float:
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
