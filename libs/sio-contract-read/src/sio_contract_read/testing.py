"""Ayudas de prueba para los adaptadores de contrato de los consumidores (spec 025, research R7).

``create_owner_schema`` prepara, en el contenedor de prueba del **consumidor**, una base ``<cons>_test__<prop>``
con el esquema real del propietario: ejecuta ``alembic upgrade head`` con el ``.venv`` del propietario, de modo
que las vistas probadas son exactamente las que publica su migración.

Las variables mínimas se toman del ``.env.example`` del propietario. Nunca se leen ``.env`` reales: Alembic se
ejecuta con ``DATABASE_URL`` y las demás variables ya fijadas, y ``load_dotenv(override=False)`` no las pisa.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from sio_contract_read.engine import chunked
from sio_contract_read.provisioning import _ident

__all__ = ["chunked", "create_owner_schema", "env_example", "database_url_for"]


def env_example(owner_service_dir: Path | str) -> dict[str, str]:
    """Pares ``CLAVE=valor`` del ``.env.example`` del propietario (sin comillas ni comentarios)."""
    path = Path(owner_service_dir) / ".env.example"
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key] = value
    return values


def database_url_for(admin_url: str, db_name: str) -> str:
    """La misma URL de administrador apuntando a otra base."""
    return make_url(admin_url).set(database=db_name).render_as_string(hide_password=False)


def create_owner_schema(
    admin_url: str,
    db_name: str,
    owner_service_dir: Path | str,
    env: Mapping[str, str] | None = None,
    *,
    recreate: bool = False,
) -> str:
    """Crea ``db_name`` si no existe y aplica las migraciones del propietario. Devuelve su URL.

    Si el propietario no tiene ``.venv/bin/alembic``, omite la prueba con ``pytest.skip``.
    """
    db_name = _ident(db_name, "base")
    owner = Path(owner_service_dir).resolve()
    alembic = owner / ".venv" / "bin" / "alembic"
    if not alembic.exists():
        import pytest

        pytest.skip(f"{owner.name}: falta {alembic.relative_to(owner)}; crea su .venv para probar el contrato.")

    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            exists = connection.execute(text("SELECT 1 FROM pg_database WHERE datname = :d"), {"d": db_name}).first()
            if exists and recreate:
                connection.execute(text(f"DROP DATABASE {db_name} WITH (FORCE)"))
                exists = None
            if not exists:
                connection.execute(text(f"CREATE DATABASE {db_name}"))
    finally:
        admin.dispose()

    url = database_url_for(admin_url, db_name)
    run_env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}
    run_env.update(env_example(owner))
    run_env.update(env or {})
    run_env["DATABASE_URL"] = url
    result = subprocess.run(
        [str(alembic), "upgrade", "head"],
        cwd=owner,
        env=run_env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        tail = "\n".join((result.stderr or result.stdout).splitlines()[-15:])
        raise RuntimeError(f"alembic upgrade head de {owner.name} falló en {db_name}:\n{tail}")
    return url


# --------------------------------------------------------------------------- roles en la base de prueba


def provision_reader(owner_url: str, grants_path: Path | str, consumer: str, password: str) -> str:
    """Aplica en ``owner_url`` los permisos de ``grants.yaml`` SOLO para ``consumer``; devuelve la URL del lector."""
    from sio_contract_read import provisioning as prov

    grants = prov.load_grants(grants_path)
    selected = tuple(item for item in grants.consumers if item.service == consumer)
    if not selected:
        raise ValueError(f"{grants_path}: {consumer} no está declarado.")
    only = prov.OwnerGrants(owner=grants.owner, abbreviation=grants.abbreviation, consumers=selected)
    engine = prov.admin_engine(owner_url)
    try:
        prov.apply_owner(engine, only, prov.database_name(owner_url), {consumer: password})
    finally:
        engine.dispose()
    return prov.reader_url(owner_url, selected[0].login_role, password)
