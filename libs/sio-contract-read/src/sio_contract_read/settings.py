"""Configuración de una lectura directa por vistas de contrato (spec 025, contracts/configuration.md).

Por cada propietario, el consumidor declara un prefijo (``PRODUCT_CATALOG``, ``OPERATIONAL_CONTEXT``…):

- ``<PREFIJO>_READ_SOURCE``: ``http`` (por defecto) o ``contract``.
- ``<PREFIJO>_CONTRACT_DATABASE_URL``: obligatoria con ``contract``; esquema ``postgresql+psycopg://``.

Comunes a todos los propietarios del consumidor:

- ``CONTRACT_READ_POOL_SIZE`` (1–10, por defecto 1)
- ``CONTRACT_READ_MAX_OVERFLOW`` (0–10, por defecto 2)
- ``CONTRACT_READ_CONNECT_TIMEOUT_SECONDS`` (1–10, por defecto 2)

El tiempo máximo de cada consulta es el de la integración HTTP equivalente, que el consumidor pasa como
``timeout_seconds``. Un valor inválido lanza ``ContractReadConfigError`` nombrando la variable.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

HTTP = "http"
CONTRACT = "contract"
_SOURCES = (HTTP, CONTRACT)
_URL_PREFIX = "postgresql+psycopg://"


class ContractReadConfigError(ValueError):
    """Configuración inválida de una lectura directa."""


def _int(env: Mapping[str, str], name: str, default: int, low: int, high: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ContractReadConfigError(f"{name} debe ser un entero entre {low} y {high}.") from None
    if not low <= value <= high:
        raise ContractReadConfigError(f"{name} debe estar entre {low} y {high}.")
    return value


@dataclass(frozen=True, slots=True)
class ContractReadSettings:
    """Fuente y conexión de lectura para un propietario."""

    prefix: str
    source: str
    database_url: str | None
    timeout_seconds: float
    pool_size: int = 1
    max_overflow: int = 2
    connect_timeout_seconds: int = 2

    @property
    def uses_contract(self) -> bool:
        return self.source == CONTRACT

    @classmethod
    def from_env(
        cls, prefix: str, *, timeout_seconds: float, env: Mapping[str, str] | None = None
    ) -> ContractReadSettings:
        values = os.environ if env is None else env
        source_name = f"{prefix}_READ_SOURCE"
        source = values.get(source_name, "").strip().lower() or HTTP
        if source not in _SOURCES:
            raise ContractReadConfigError(f"{source_name} debe ser 'http' o 'contract'.")

        url_name = f"{prefix}_CONTRACT_DATABASE_URL"
        url = values.get(url_name, "").strip() or None
        if source == CONTRACT:
            if url is None:
                raise ContractReadConfigError(f"{url_name} es obligatoria cuando {source_name}=contract.")
            if not url.startswith(_URL_PREFIX):
                raise ContractReadConfigError(f"{url_name} debe empezar por {_URL_PREFIX}")

        if not timeout_seconds > 0:
            raise ContractReadConfigError(f"El tiempo máximo de lectura de {prefix} debe ser mayor que 0.")

        return cls(
            prefix=prefix,
            source=source,
            database_url=url,
            timeout_seconds=float(timeout_seconds),
            pool_size=_int(values, "CONTRACT_READ_POOL_SIZE", 1, 1, 10),
            max_overflow=_int(values, "CONTRACT_READ_MAX_OVERFLOW", 2, 0, 10),
            connect_timeout_seconds=_int(values, "CONTRACT_READ_CONNECT_TIMEOUT_SECONDS", 2, 1, 10),
        )
