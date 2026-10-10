"""Configuración de la suite: URL de los servicios, variables y contenedores gestionados.

Las URL usan `127.0.0.1` y los puertos de `docs/port-map.md` (research R-03); cada una se puede
sobrescribir con `SIO_MVP_<SERVICIO>_URL`. Las variables se leen del entorno y, si faltan, de
`infrastructure/.env`, sin copiarlas ni imprimirlas (Principio IX, RC-05).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[3]
INFRASTRUCTURE_ENV = REPO_ROOT / "infrastructure" / ".env"

DEFAULT_TOKEN_URL = "http://127.0.0.1:8081/realms/sio/protocol/openid-connect/token"
DEFAULT_AUDIT_BACKOFF_MAX_SECONDS = 300.0  # libs/sio-audit/src/sio_audit/worker/settings.py
SENSITIVE_NAME = re.compile(r"(SECRET|PASSWORD|TOKEN)", re.IGNORECASE)


@dataclass(frozen=True)
class Service:
    key: str
    port: int
    api_prefix: str
    has_worker: bool = False
    has_reconciler: bool = False

    @property
    def env_name(self) -> str:
        return self.key.upper().replace("-", "_")

    @property
    def container(self) -> str:
        return f"sio-{self.key}-service"

    @property
    def db_container(self) -> str:
        return f"sio-{self.key}-db"

    @property
    def test_db_container(self) -> str:
        return f"sio-{self.key}-test-db"

    @property
    def worker_container(self) -> str | None:
        return f"sio-{self.key}-audit-outbox-worker" if self.has_worker else None

    @property
    def reconciler_container(self) -> str | None:
        return f"sio-{self.key}-reconciler" if self.has_reconciler else None

    @property
    def project(self) -> str:
        return f"{self.key}-service"

    @property
    def source_dir(self) -> Path:
        return REPO_ROOT / "services" / self.project


# Orden y puertos de docs/port-map.md. Geography y Payment Reference publican sus rutas sin /api/v1.
SERVICES: tuple[Service, ...] = (
    Service("party-identity", 8101, "/api/v1", has_worker=True),
    Service("geography", 8102, ""),
    Service("product-catalog", 8103, "/api/v1", has_worker=True),
    Service("operational-context", 8104, "/api/v1", has_worker=True),
    Service("payment-reference", 8105, ""),
    Service("commercial-relationship", 8106, "/api/v1", has_worker=True),
    Service("purchase", 8107, "/api/v1", has_worker=True, has_reconciler=True),
    Service("sales", 8108, "/api/v1", has_worker=True, has_reconciler=True),
    Service("inventory", 8109, "/api/v1", has_worker=True),
    Service("audit", 8110, "/api/v1"),
)
SERVICES_BY_KEY = {service.key: service for service in SERVICES}


def service(key: str) -> Service:
    try:
        return SERVICES_BY_KEY[key]
    except KeyError as error:
        raise KeyError(f"Servicio desconocido: {key}") from error


def managed_containers() -> list[str]:
    """Contenedores que la suite puede detener y que restaura siempre (runner-cli §4)."""
    names: list[str] = []
    names += [item.container for item in SERVICES]
    names += [item.db_container for item in SERVICES]
    names += [item.worker_container for item in SERVICES if item.worker_container]
    names += [item.reconciler_container for item in SERVICES if item.reconciler_container]
    names.append("sio-keycloak")
    return names


class Secret:
    """Valor sensible que nunca se muestra en `repr`, `str` ni en formatos."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret(***)"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return repr(self)


def read_env_file(path: Path) -> dict[str, str]:
    """Lee un archivo `KEY=VALUE` (comentarios y comillas simples o dobles)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if name.startswith("export "):
            name = name[len("export ") :].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[name] = value
    return values


@dataclass(frozen=True)
class Settings:
    urls: Mapping[str, str]
    token_url: str
    audit_wait_seconds: float
    guide_write: bool
    _variables: Mapping[str, str] = field(repr=False)

    def service_url(self, key: str) -> str:
        return self.urls[service(key).key]

    def api_base(self, key: str) -> str:
        return self.service_url(key) + service(key).api_prefix

    def value(self, name: str) -> str | None:
        """Variable no sensible (puertos, nombres de base, usuarios)."""
        if SENSITIVE_NAME.search(name):
            raise ValueError(f"{name} es sensible: use secret()")
        return self._variables.get(name) or None

    def secret(self, name: str) -> Secret | None:
        value = self._variables.get(name)
        return Secret(value) if value else None

    def sensitive_values(self) -> set[str]:
        """Valores de `*SECRET*`, `*PASSWORD*`, `*TOKEN*` para filtrarlos de informes (RC-05)."""
        return {value for name, value in self._variables.items() if value and SENSITIVE_NAME.search(name)}

    def __repr__(self) -> str:
        return f"Settings(urls={dict(self.urls)!r}, token_url={self.token_url!r})"

    __str__ = __repr__


def load_settings(environ: Mapping[str, str] | None = None, env_file: Path | None = None) -> Settings:
    environ = os.environ if environ is None else environ
    variables = read_env_file(INFRASTRUCTURE_ENV if env_file is None else env_file)
    variables.update({name: value for name, value in environ.items() if value is not None})

    urls = {}
    for item in SERVICES:
        override = environ.get(f"SIO_MVP_{item.env_name}_URL", "").strip()
        urls[item.key] = override.rstrip("/") if override else f"http://127.0.0.1:{item.port}"

    if environ.get("SIO_MVP_AUDIT_WAIT_SECONDS"):
        audit_wait = float(environ["SIO_MVP_AUDIT_WAIT_SECONDS"])
    else:
        backoff = variables.get("AUDIT_OUTBOX_BACKOFF_MAX_SECONDS")
        audit_wait = (float(backoff) if backoff else DEFAULT_AUDIT_BACKOFF_MAX_SECONDS) + 60.0

    return Settings(
        urls=urls,
        token_url=(environ.get("SIO_MVP_KEYCLOAK_TOKEN_URL") or DEFAULT_TOKEN_URL).strip(),
        audit_wait_seconds=audit_wait,
        guide_write=environ.get("SIO_MVP_GUIDE_WRITE", "").strip() == "1",
        _variables=variables,
    )
