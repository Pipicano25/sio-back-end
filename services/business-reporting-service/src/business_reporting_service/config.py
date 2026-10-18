"""Configuración de business-reporting-service (variables de entorno, Principio IX).

Sin secretos propios: el servicio no tiene cliente técnico (spec 023, DR-07) y consulta a los propietarios con el
token del usuario. Tiempos (FR-023-51): 5 s por dependencia, 10 s por reporte JSON y 120 s por CSV.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuración del microservicio. Las URL de las dependencias incluyen `/api/v1`."""

    docs_enabled: bool
    operational_context_base_url: str
    sales_base_url: str
    purchase_base_url: str
    inventory_base_url: str
    commercial_relationship_base_url: str
    product_catalog_base_url: str
    jwks_url: str | None = None
    dependency_timeout_seconds: float = 5.0
    json_budget_seconds: float = 10.0
    csv_budget_seconds: float = 120.0
    max_parallel_calls: int = 4
    max_period_days: int = 366
    csv_max_rows: int = 50_000
    default_timezone: str = "America/Bogota"

    def __post_init__(self) -> None:
        if self.dependency_timeout_seconds > self.json_budget_seconds:
            raise RuntimeError("BRS_JSON_BUDGET_SECONDS debe ser al menos BRS_DEPENDENCY_TIMEOUT_SECONDS.")
        if self.json_budget_seconds > self.csv_budget_seconds:
            raise RuntimeError("BRS_CSV_BUDGET_SECONDS debe ser al menos BRS_JSON_BUDGET_SECONDS.")
        for name, value in (("BRS_MAX_PARALLEL_CALLS", self.max_parallel_calls),
                            ("BRS_MAX_PERIOD_DAYS", self.max_period_days), ("BRS_CSV_MAX_ROWS", self.csv_max_rows)):
            if value < 1:
                raise RuntimeError(f"{name} debe ser al menos 1.")

    def __repr__(self) -> str:
        return f"Settings(docs_enabled={self.docs_enabled!r})"


def load_settings() -> Settings:
    """Carga la configuración desde variables de entorno.

    Raises:
        RuntimeError: Si falta una variable obligatoria o tiene un valor inválido.
    """
    return Settings(
        docs_enabled=_read_bool("SIO_DOCS_ENABLED", default=False),
        operational_context_base_url=_required_text("OPERATIONAL_CONTEXT_SERVICE_BASE_URL"),
        sales_base_url=_required_text("SALES_SERVICE_BASE_URL"),
        purchase_base_url=_required_text("PURCHASE_SERVICE_BASE_URL"),
        inventory_base_url=_required_text("INVENTORY_SERVICE_BASE_URL"),
        commercial_relationship_base_url=_required_text("COMMERCIAL_RELATIONSHIP_SERVICE_BASE_URL"),
        product_catalog_base_url=_required_text("PRODUCT_CATALOG_SERVICE_BASE_URL"),
        jwks_url=_optional_text("SIO_AUTH_JWKS_URL"),
        dependency_timeout_seconds=_read_positive_float("BRS_DEPENDENCY_TIMEOUT_SECONDS", 5.0),
        json_budget_seconds=_read_positive_float("BRS_JSON_BUDGET_SECONDS", 10.0),
        csv_budget_seconds=_read_positive_float("BRS_CSV_BUDGET_SECONDS", 120.0),
        max_parallel_calls=_read_positive_int("BRS_MAX_PARALLEL_CALLS", 4),
        max_period_days=_read_positive_int("BRS_MAX_PERIOD_DAYS", 366),
        csv_max_rows=_read_positive_int("BRS_CSV_MAX_ROWS", 50_000),
        default_timezone=_optional_text("BRS_DEFAULT_TIMEZONE") or "America/Bogota",
    )


def _required_text(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"La variable de entorno {name} es obligatoria y no puede estar vacía.")
    return value.strip()


def _optional_text(name: str) -> str | None:
    value = os.getenv(name)
    return None if value is None or not value.strip() else value.strip()


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
