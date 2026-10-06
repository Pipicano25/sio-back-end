"""Configuración de Audit Service (variables de entorno, Principio IX)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuración del microservicio.

    No existen modos por entorno: Operational Context se consume siempre con el
    mismo contrato y un único adaptador real; las pruebas inyectan dobles por DI.

    Attributes:
        docs_enabled: Swagger y OpenAPI habilitados (`SIO_DOCS_ENABLED`).
        database_url: URL de conexión a la base propia.
        operational_context_base_url: URL base de Operational Context, con `/api/v1`.
        operational_context_timeout_seconds: Tiempo de espera de `operational-access`.
        max_clock_skew_seconds: Tolerancia de `occurred_at` hacia el futuro (DS-08).
    """

    docs_enabled: bool
    database_url: str
    operational_context_base_url: str
    operational_context_timeout_seconds: float = 5.0
    max_clock_skew_seconds: int = 300


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
        operational_context_base_url=_read_text(
            "OPERATIONAL_CONTEXT_SERVICE_BASE_URL",
            default="http://localhost:8104/api/v1",
        ),
        operational_context_timeout_seconds=_read_positive_float(
            "OPERATIONAL_CONTEXT_TIMEOUT_SECONDS",
            default=5.0,
        ),
        max_clock_skew_seconds=_read_positive_int("AUDIT_MAX_CLOCK_SKEW_SECONDS", default=300),
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


def _read_positive_int(name: str, *, default: int) -> int:
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"La variable de entorno {name} debe ser un entero.") from exc

    if parsed <= 0:
        raise RuntimeError(f"La variable de entorno {name} debe ser mayor que cero.")

    return parsed
