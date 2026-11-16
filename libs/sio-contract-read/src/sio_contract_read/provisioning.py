"""Roles de lectura de las vistas de contrato (spec 025, contracts/reader-roles.md).

Cada propietario declara en ``services/<propietario>/contract/grants.yaml`` qué consumidor lee qué vista. Por
cada pareja se crean:

- ``contract_<prop>__<cons>`` (NOLOGIN): ``CONNECT`` a la base, ``USAGE`` en ``contract`` y ``SELECT`` solo en sus vistas.
- ``<cons>_contract_reader`` (LOGIN, solo lectura): miembro de sus roles de acceso.

Todo es idempotente. Ninguna función imprime contraseñas ni URL.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

_IDENT = re.compile(r"^[a-z][a-z0-9_]{0,40}$")


class ProvisioningError(RuntimeError):
    """Declaración inválida o fallo al aplicar los permisos."""


def _ident(value: str, what: str) -> str:
    if not _IDENT.match(value):
        raise ProvisioningError(f"{what} inválido: {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class ConsumerGrant:
    service: str
    abbreviation: str
    views: tuple[str, ...]

    @property
    def login_role(self) -> str:
        return f"{self.abbreviation}_contract_reader"


@dataclass(frozen=True, slots=True)
class OwnerGrants:
    owner: str
    abbreviation: str
    consumers: tuple[ConsumerGrant, ...] = field(default_factory=tuple)
    revoke_public_connect: bool = False

    def access_role(self, consumer: ConsumerGrant) -> str:
        return f"contract_{self.abbreviation}__{consumer.abbreviation}"


def load_grants(path: Path | str) -> OwnerGrants:
    """Lee y valida un ``grants.yaml``."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    owner = str(data.get("owner", "")).strip()
    abbreviation = _ident(str(data.get("abbreviation", "")).strip(), "abbreviation")
    consumers = []
    for service, spec in sorted((data.get("consumers") or {}).items()):
        views = tuple(_ident(str(view), "vista") for view in (spec or {}).get("views") or ())
        if not views:
            raise ProvisioningError(f"{path}: el consumidor {service} no declara vistas.")
        consumers.append(
            ConsumerGrant(
                service=str(service),
                abbreviation=_ident(str((spec or {}).get("abbreviation", "")).strip(), "abbreviation"),
                views=views,
            )
        )
    if not owner:
        raise ProvisioningError(f"{path}: falta 'owner'.")
    return OwnerGrants(
        owner=owner,
        abbreviation=abbreviation,
        consumers=tuple(consumers),
        revoke_public_connect=bool(data.get("revoke_public_connect", False)),
    )


def admin_engine(url: str) -> Engine:
    return create_engine(url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def ensure_login_role(engine: Engine, role: str, password: str) -> None:
    """Crea o actualiza el rol de conexión de un consumidor (sin superusuario, solo lectura)."""
    role = _ident(role, "rol")
    if not password:
        raise ProvisioningError(f"Falta la contraseña del rol {role}.")
    with engine.connect() as connection:
        exists = connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role}).first()
        verb = "ALTER" if exists else "CREATE"
        connection.execute(
            text(
                f"{verb} ROLE {role} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT "
                f"PASSWORD {_quote_literal(password)}"
            )
        )
        connection.execute(text(f"ALTER ROLE {role} SET default_transaction_read_only = on"))


def apply_owner(engine: Engine, grants: OwnerGrants, database: str, passwords: dict[str, str]) -> list[str]:
    """Aplica los permisos de un propietario en su base. Devuelve un resumen sin secretos."""
    database = _ident(database, "base")
    summary: list[str] = []
    with engine.connect() as connection:
        present = {
            row[0]
            for row in connection.execute(
                text("SELECT table_name FROM information_schema.views WHERE table_schema = 'contract'")
            )
        }
    for consumer in grants.consumers:
        missing = [view for view in consumer.views if view not in present]
        if missing:
            raise ProvisioningError(
                f"{grants.owner}: vistas declaradas para {consumer.service} que no existen: {', '.join(missing)}"
            )
        ensure_login_role(engine, consumer.login_role, passwords.get(consumer.service, ""))
        access = grants.access_role(consumer)
        with engine.connect() as connection:
            if not connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": access}).first():
                connection.execute(text(f"CREATE ROLE {access} NOLOGIN"))
            connection.execute(text(f"GRANT CONNECT ON DATABASE {database} TO {access}"))
            connection.execute(text(f"GRANT USAGE ON SCHEMA contract TO {access}"))
            for view in sorted(present):
                verb = "GRANT" if view in consumer.views else "REVOKE"
                prep = "TO" if verb == "GRANT" else "FROM"
                connection.execute(text(f"{verb} SELECT ON contract.{view} {prep} {access}"))
            connection.execute(text(f"GRANT {access} TO {consumer.login_role}"))
        summary.append(f"{grants.owner} → {consumer.service}: {len(consumer.views)} vistas")
    if grants.revoke_public_connect:
        with engine.connect() as connection:
            connection.execute(text(f"REVOKE CONNECT ON DATABASE {database} FROM PUBLIC"))
    return summary


@dataclass(frozen=True, slots=True)
class Check:
    pair: str
    name: str
    ok: bool

    def line(self) -> str:
        return f"{'OK   ' if self.ok else 'FALLA'} {self.pair}: {self.name}"


def _expect_denied(engine: Engine, sql: str) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text(sql))
    except DBAPIError:
        return True
    return False


def verify_pair(reader_url: str, grants: OwnerGrants, consumer: ConsumerGrant, *, probe_table: str) -> list[Check]:
    """Comprueba que el rol del consumidor lee sus vistas y nada más (SC-008)."""
    pair = f"{grants.abbreviation}→{consumer.abbreviation}"
    engine = create_engine(reader_url, pool_pre_ping=True)
    checks: list[Check] = []
    try:
        for view in consumer.views:
            try:
                with engine.connect() as connection:
                    connection.execute(text(f"SELECT 1 FROM contract.{view} LIMIT 1"))
                checks.append(Check(pair, f"lee contract.{view}", True))
            except DBAPIError:
                checks.append(Check(pair, f"lee contract.{view}", False))
        table = _ident(probe_table, "tabla")
        checks.append(Check(pair, f"no lee public.{table}", _expect_denied(engine, f"SELECT 1 FROM public.{table} LIMIT 1")))
        checks.append(Check(pair, "no escribe", _expect_denied(engine, "CREATE TEMP TABLE sio_contract_probe (x int)")))
        others = [
            view
            for other in grants.consumers
            if other.abbreviation != consumer.abbreviation
            for view in other.views
            if view not in consumer.views
        ]
        if others:
            view = others[0]
            checks.append(
                Check(pair, f"no lee contract.{view}", _expect_denied(engine, f"SELECT 1 FROM contract.{view} LIMIT 1"))
            )
    finally:
        engine.dispose()
    return checks


def reader_url(admin_url: str, role: str, password: str) -> str:
    """URL del rol de lectura sobre la misma base y servidor que ``admin_url``."""
    url = make_url(admin_url).set(username=role, password=password)
    return url.render_as_string(hide_password=False)


def database_name(url: str) -> str:
    name = make_url(url).database or ""
    return _ident(name, "base")


def discover(services_dir: Path | str) -> list[tuple[Path, OwnerGrants]]:
    """Todos los ``contract/grants.yaml`` de los servicios."""
    found = []
    for path in sorted(Path(services_dir).glob("*/contract/grants.yaml")):
        found.append((path, load_grants(path)))
    return found


def consumers_of(owners: Iterable[OwnerGrants]) -> set[str]:
    return {consumer.service for owner in owners for consumer in owner.consumers}
