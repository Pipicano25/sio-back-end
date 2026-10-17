"""Configuración de product-inventory-query-service (variables de entorno, Principio IX).

No hay modos por entorno: las dependencias y Keycloak se consumen siempre con su adaptador real;
las pruebas inyectan dobles en `create_app` (spec 022, research.md R-17).

Coherencia de tiempos (RNF-022-3, FR-022-136): la búsqueda progresiva se detiene entre lotes al
agotar `work_time_seconds` contados desde el inicio de la solicitud; después queda, como mínimo,
el tiempo de una llamada (`dependency_timeout_seconds`) para el enriquecimiento de la página.
Por eso `work_time_seconds + dependency_timeout_seconds <= request_budget_seconds` (5 + 3 <= 8).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

MIN_SECRET_BYTES = 32
"""Longitud mínima del secreto del cursor (HMAC-SHA256, research.md R-08)."""

MAX_BATCH = 100
"""Los lotes de los conductores y evaluadores admiten como máximo 100 ids (research.md R-10)."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuración del microservicio. Las URL de las dependencias incluyen `/api/v1`."""

    docs_enabled: bool
    operational_context_base_url: str
    commercial_relationship_base_url: str
    product_catalog_base_url: str
    inventory_base_url: str
    keycloak_token_url: str
    client_id: str
    client_secret: str
    cursor_secret: str
    cursor_secret_previous: str | None = None
    jwks_url: str | None = None
    dependency_timeout_seconds: float = 3.0
    request_budget_seconds: float = 8.0
    work_time_seconds: float = 5.0
    max_batches_per_request: int = 5
    batch_min: int = 20
    batch_factor: int = 2
    batch_max: int = 40
    max_parallel_calls: int = 8
    cursor_ttl_seconds: int = 900
    reference_cache_seconds: float = 300.0

    def __post_init__(self) -> None:
        if len(self.cursor_secret.encode("utf-8")) < MIN_SECRET_BYTES:
            raise RuntimeError(f"PIQS_CURSOR_SECRET debe tener al menos {MIN_SECRET_BYTES} bytes.")

        if self.cursor_secret_previous is not None:
            if len(self.cursor_secret_previous.encode("utf-8")) < MIN_SECRET_BYTES:
                raise RuntimeError(f"PIQS_CURSOR_SECRET_PREVIOUS debe tener al menos {MIN_SECRET_BYTES} bytes.")
            if self.cursor_secret_previous == self.cursor_secret:
                raise RuntimeError("PIQS_CURSOR_SECRET_PREVIOUS debe ser distinto de PIQS_CURSOR_SECRET.")

        if self.work_time_seconds + self.dependency_timeout_seconds > self.request_budget_seconds:
            raise RuntimeError(
                "PIQS_REQUEST_BUDGET_SECONDS debe ser al menos PIQS_WORK_TIME_SECONDS + "
                "PIQS_DEPENDENCY_TIMEOUT_SECONDS."
            )

        if not 1 <= self.batch_min <= self.batch_max <= MAX_BATCH:
            raise RuntimeError(f"Se requiere 1 <= PIQS_BATCH_MIN <= PIQS_BATCH_MAX <= {MAX_BATCH}.")

        for name, value in (
            ("PIQS_BATCH_FACTOR", self.batch_factor),
            ("PIQS_MAX_BATCHES_PER_REQUEST", self.max_batches_per_request),
            ("PIQS_MAX_PARALLEL_CALLS", self.max_parallel_calls),
            ("PIQS_CURSOR_TTL_SECONDS", self.cursor_ttl_seconds),
        ):
            if value < 1:
                raise RuntimeError(f"{name} debe ser al menos 1.")

    def __repr__(self) -> str:  # nunca muestra secretos
        return f"Settings(client_id={self.client_id!r}, docs_enabled={self.docs_enabled!r})"

    def batch_size(self, page_size: int) -> int:
        """`min(max(page_size × factor, mínimo), máximo)` (FR-022-133)."""
        return min(max(page_size * self.batch_factor, self.batch_min), self.batch_max)


def load_settings() -> Settings:
    """Carga la configuración desde variables de entorno.

    Raises:
        RuntimeError: Si falta una variable obligatoria o tiene un valor inválido.
    """
    return Settings(
        docs_enabled=_read_bool("SIO_DOCS_ENABLED", default=False),
        operational_context_base_url=_required_text("OPERATIONAL_CONTEXT_SERVICE_BASE_URL"),
        commercial_relationship_base_url=_required_text("COMMERCIAL_RELATIONSHIP_SERVICE_BASE_URL"),
        product_catalog_base_url=_required_text("PRODUCT_CATALOG_SERVICE_BASE_URL"),
        inventory_base_url=_required_text("INVENTORY_SERVICE_BASE_URL"),
        keycloak_token_url=_required_text("KEYCLOAK_TOKEN_URL"),
        client_id=_read_text("PIQS_CLIENT_ID", default="product-inventory-query-service"),
        client_secret=_required_text("PIQS_CLIENT_SECRET"),
        cursor_secret=_required_text("PIQS_CURSOR_SECRET"),
        cursor_secret_previous=_optional_text("PIQS_CURSOR_SECRET_PREVIOUS"),
        jwks_url=_optional_text("SIO_AUTH_JWKS_URL"),
        dependency_timeout_seconds=_read_positive_float("PIQS_DEPENDENCY_TIMEOUT_SECONDS", 3.0),
        request_budget_seconds=_read_positive_float("PIQS_REQUEST_BUDGET_SECONDS", 8.0),
        work_time_seconds=_read_positive_float("PIQS_WORK_TIME_SECONDS", 5.0),
        max_batches_per_request=_read_positive_int("PIQS_MAX_BATCHES_PER_REQUEST", 5),
        batch_min=_read_positive_int("PIQS_BATCH_MIN", 20),
        batch_factor=_read_positive_int("PIQS_BATCH_FACTOR", 2),
        batch_max=_read_positive_int("PIQS_BATCH_MAX", 40),
        max_parallel_calls=_read_positive_int("PIQS_MAX_PARALLEL_CALLS", 8),
        cursor_ttl_seconds=_read_positive_int("PIQS_CURSOR_TTL_SECONDS", 900),
        reference_cache_seconds=_read_positive_float("PIQS_REFERENCE_CACHE_SECONDS", 300.0),
    )


def _required_text(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(f"La variable de entorno {name} es obligatoria y no puede estar vacía.")

    return value.strip()


def _optional_text(name: str) -> str | None:
    value = os.getenv(name)
    return None if value is None or not value.strip() else value.strip()


def _read_text(name: str, *, default: str) -> str:
    return _optional_text(name) or default


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


def _read_positive_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"La variable de entorno {name} debe ser un entero.") from exc

    if parsed < 1:
        raise RuntimeError(f"La variable de entorno {name} debe ser al menos 1.")

    return parsed
