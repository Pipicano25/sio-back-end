"""Motor de solo lectura hacia la base de un propietario (spec 025, research R3).

Cada conexión abre con ``default_transaction_read_only=on`` y ``statement_timeout`` igual al tiempo máximo de la
integración. El pool es pequeño y su espera tampoco supera ese tiempo.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import Engine, create_engine, text

from sio_contract_read.settings import ContractReadConfigError, ContractReadSettings


def connect_options(settings: ContractReadSettings, application_name: str) -> str:
    """Opciones de sesión de PostgreSQL para cada conexión de lectura."""
    milliseconds = max(1, int(settings.timeout_seconds * 1000))
    name = "".join(ch for ch in application_name if ch.isalnum() or ch in "-_")[:60] or "sio-contract-read"
    return f"-c statement_timeout={milliseconds} -c default_transaction_read_only=on -c application_name={name}"


def create_contract_engine(settings: ContractReadSettings, *, application_name: str) -> Engine:
    """Crea el motor de lectura. Exige ``source=contract`` y URL."""
    if not settings.uses_contract or settings.database_url is None:
        raise ContractReadConfigError(f"{settings.prefix}: el motor de lectura solo se crea con READ_SOURCE=contract.")
    return create_engine(
        settings.database_url,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.timeout_seconds,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": settings.connect_timeout_seconds,
            "options": connect_options(settings, application_name),
        },
    )


def read(engine: Engine, sql: str, params: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Ejecuta una consulta de lectura y devuelve las filas como diccionarios."""
    with engine.connect() as connection:
        result = connection.execute(text(sql), dict(params or {}))
        return [dict(row) for row in result.mappings()]


def read_one(engine: Engine, sql: str, params: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Primera fila o ``None``."""
    rows = read(engine, sql, params)
    return rows[0] if rows else None


def chunked(values: Iterable[Any], size: int = 100) -> list[list[Any]]:
    """Trozos de como máximo ``size`` elementos, en el orden recibido."""
    items = list(values)
    return [items[index : index + size] for index in range(0, len(items), size)]
