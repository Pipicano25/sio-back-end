"""Configuración del worker por variables de entorno (R-12)."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


class WorkerConfigurationError(RuntimeError):
    """Falta una variable obligatoria o tiene un valor inválido (el proceso sale con código ≠ 0)."""


DEFAULT_HEARTBEAT_FILE = str(Path(tempfile.gettempdir()) / "sio-audit-worker.heartbeat")


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    """Parámetros del `audit-outbox-worker`."""

    database_url: str
    audit_base_url: str
    keycloak_base_url: str
    keycloak_realm: str
    client_id: str
    client_secret: str = field(repr=False)
    poll_interval_seconds: float = 2.0
    http_timeout_seconds: float = 5.0
    backoff_initial_seconds: float = 1.0
    backoff_factor: float = 2.0
    backoff_max_seconds: float = 300.0
    batch_size: int = 100
    heartbeat_file: str = DEFAULT_HEARTBEAT_FILE

    @property
    def token_url(self) -> str:
        return f"{self.keycloak_base_url.rstrip('/')}/realms/{self.keycloak_realm}/protocol/openid-connect/token"

    @property
    def heartbeat_max_age_seconds(self) -> float:
        return 3 * self.poll_interval_seconds + self.http_timeout_seconds

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> WorkerSettings:
        env = os.environ if environ is None else environ

        def required(name: str) -> str:
            value = env.get(name)
            if value is None or not value.strip():
                raise WorkerConfigurationError(f"La variable de entorno {name} es obligatoria.")
            return value.strip()

        def number(name: str, default: float, *, minimum: float = 0.0, exclusive: bool = True) -> float:
            value = env.get(name)
            if value is None or not value.strip():
                return default
            try:
                parsed = float(value)
            except ValueError as exc:
                raise WorkerConfigurationError(f"La variable de entorno {name} debe ser numérica.") from exc
            if parsed < minimum or (exclusive and parsed == minimum):
                raise WorkerConfigurationError(f"La variable de entorno {name} está fuera de rango.")
            return parsed

        batch_size = int(number("AUDIT_OUTBOX_BATCH_SIZE", 100))
        if not 1 <= batch_size <= 100:
            raise WorkerConfigurationError("AUDIT_OUTBOX_BATCH_SIZE debe estar entre 1 y 100.")

        backoff_factor = number("AUDIT_OUTBOX_BACKOFF_FACTOR", 2.0, minimum=1.0, exclusive=False)
        initial = number("AUDIT_OUTBOX_BACKOFF_INITIAL_SECONDS", 1.0)
        maximum = number("AUDIT_OUTBOX_BACKOFF_MAX_SECONDS", 300.0)
        if maximum < initial:
            raise WorkerConfigurationError(
                "AUDIT_OUTBOX_BACKOFF_MAX_SECONDS no puede ser menor que el backoff inicial."
            )

        return cls(
            database_url=required("DATABASE_URL"),
            audit_base_url=required("AUDIT_SERVICE_BASE_URL").rstrip("/"),
            keycloak_base_url=required("KEYCLOAK_BASE_URL"),
            keycloak_realm=required("KEYCLOAK_REALM"),
            client_id=required("AUDIT_CLIENT_ID"),
            client_secret=required("AUDIT_CLIENT_SECRET"),
            poll_interval_seconds=number("AUDIT_OUTBOX_POLL_INTERVAL_SECONDS", 2.0),
            http_timeout_seconds=number("AUDIT_OUTBOX_HTTP_TIMEOUT_SECONDS", 5.0),
            backoff_initial_seconds=initial,
            backoff_factor=backoff_factor,
            backoff_max_seconds=maximum,
            batch_size=batch_size,
            heartbeat_file=env.get("AUDIT_OUTBOX_HEARTBEAT_FILE", "").strip() or DEFAULT_HEARTBEAT_FILE,
        )
