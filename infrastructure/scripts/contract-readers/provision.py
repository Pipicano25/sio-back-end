#!/usr/bin/env python3
"""Roles de lectura de las vistas de contrato (constitución 3.0.0, D27; spec 025, contracts/reader-roles.md).

Uso, desde la raíz del repositorio y después de las migraciones de los propietarios:

    python infrastructure/scripts/contract-readers/provision.py aplicar   --entorno local|aislada|servidor
    python infrastructure/scripts/contract-readers/provision.py verificar --entorno local|aislada|servidor

Entradas (variables de entorno; nunca se imprimen):

- CONTRACT_ADMIN_URL_<PROPIETARIO>: URL de un usuario dueño de la base del propietario y con CREATEROLE,
  por ejemplo CONTRACT_ADMIN_URL_OPERATIONAL_CONTEXT.
- CONTRACT_READER_PASSWORD_<CONSUMIDOR>: contraseña del rol <cons>_contract_reader, por ejemplo
  CONTRACT_READER_PASSWORD_SALES.

Lee services/*/contract/grants.yaml. Es idempotente. "verificar" termina con código 1 si un rol de lectura puede
leer una tabla, escribir o leer una vista que no le corresponde, o no puede leer las suyas (SC-008).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
try:
    from sio_contract_read import provisioning as prov
except ModuleNotFoundError:  # sin instalar: se usa el código del repositorio
    sys.path.insert(0, str(REPO / "libs" / "sio-contract-read" / "src"))
    from sio_contract_read import provisioning as prov

from sqlalchemy import text  # noqa: E402

MIN_SERVER_PASSWORD = 20


def env_name(service: str) -> str:
    return service.removesuffix("-service").replace("-", "_").upper()


def admin_url_for(owner: str) -> str:
    name = f"CONTRACT_ADMIN_URL_{env_name(owner)}"
    value = os.environ.get(name, "").strip()
    if not value:
        raise prov.ProvisioningError(f"Falta la variable {name}.")
    return value


def passwords_for(owner: prov.OwnerGrants, entorno: str) -> dict[str, str]:
    passwords: dict[str, str] = {}
    for consumer in owner.consumers:
        name = f"CONTRACT_READER_PASSWORD_{env_name(consumer.service)}"
        value = os.environ.get(name, "")
        if not value:
            raise prov.ProvisioningError(f"Falta la variable {name}.")
        if entorno == "servidor" and len(value) < MIN_SERVER_PASSWORD:
            raise prov.ProvisioningError(f"{name} debe tener al menos {MIN_SERVER_PASSWORD} caracteres en el servidor.")
        passwords[consumer.service] = value
    return passwords


def select_owners(services_dir: Path, only: list[str]) -> list[prov.OwnerGrants]:
    owners = [grants for _, grants in prov.discover(services_dir)]
    if only:
        unknown = sorted(set(only) - {owner.owner for owner in owners})
        if unknown:
            raise prov.ProvisioningError(f"Propietarios sin contract/grants.yaml: {', '.join(unknown)}")
        owners = [owner for owner in owners if owner.owner in only]
    return owners


def probe_table(admin_url: str) -> str:
    engine = prov.admin_engine(admin_url)
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name LIMIT 1"
                )
            ).first()
    finally:
        engine.dispose()
    if row is None:
        raise prov.ProvisioningError("La base del propietario no tiene tablas en public; ¿faltan las migraciones?")
    return row[0]


def apply(owners: list[prov.OwnerGrants], entorno: str) -> int:
    for owner in owners:
        url = admin_url_for(owner.owner)
        engine = prov.admin_engine(url)
        try:
            for line in prov.apply_owner(engine, owner, prov.database_name(url), passwords_for(owner, entorno)):
                print(f"OK    {line}")
        finally:
            engine.dispose()
    return 0


def verify(owners: list[prov.OwnerGrants], entorno: str) -> int:
    failures = 0
    for owner in owners:
        url = admin_url_for(owner.owner)
        passwords = passwords_for(owner, entorno)
        table = probe_table(url)
        for consumer in owner.consumers:
            reader = prov.reader_url(url, consumer.login_role, passwords[consumer.service])
            for check in prov.verify_pair(reader, owner, consumer, probe_table=table):
                print(check.line())
                failures += 0 if check.ok else 1
    print(f"{'Sin fallas' if failures == 0 else f'{failures} fallas'}.")
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Roles de lectura de las vistas de contrato (D27).")
    parser.add_argument("comando", choices=["aplicar", "verificar"])
    parser.add_argument("--entorno", required=True, choices=["local", "aislada", "servidor"])
    parser.add_argument("--propietario", action="append", default=[], help="limita a estos propietarios (repetible)")
    parser.add_argument("--services-dir", type=Path, default=REPO / "services")
    args = parser.parse_args(argv)
    try:
        owners = select_owners(args.services_dir, args.propietario)
        if not owners:
            print("No hay contract/grants.yaml que aplicar.")
            return 0
        return (apply if args.comando == "aplicar" else verify)(owners, args.entorno)
    except prov.ProvisioningError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - nunca se imprime la URL ni la traza con secretos
        print(f"Error: {type(exc).__name__} al conectar o aplicar permisos (detalle omitido).", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
