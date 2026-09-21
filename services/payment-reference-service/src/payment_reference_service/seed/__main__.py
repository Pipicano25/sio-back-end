"""Carga explícita de datos iniciales de Payment Reference Service.

El proceso de seed está separado de las migraciones Alembic y no se
ejecuta durante el arranque de FastAPI.

Los registros se identifican mediante su código único. Si un código ya
existe, se conserva el registro actual y no se crea un duplicado.
"""
"""CLI para cargar los datos iniciales de Payment Reference Service."""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import SQLAlchemyError


# ============================================================
# CARGA DE ENTORNO
# ============================================================

SERVICE_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = SERVICE_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)

# Si DATABASE_URL existe en el entorno pero está vacía, permitimos que
# el .env local la complete. Una variable real no vacía proporcionada
# por Docker Compose conserva prioridad.
if not (os.getenv("DATABASE_URL") or "").strip():
    load_dotenv(
        dotenv_path=ENV_FILE,
        override=True,
    )

if not (os.getenv("DATABASE_URL") or "").strip():
    raise RuntimeError(
        "No fue posible cargar DATABASE_URL desde el entorno ni desde "
        f"el archivo {ENV_FILE}."
    )


# IMPORTANTE:
# Estos imports deben permanecer DESPUÉS de load_dotenv().
from payment_reference_service.infrastructure.database import (  # noqa: E402
    SessionLocal,
    engine,
)
from payment_reference_service.infrastructure.models import (  # noqa: E402
    GlobalPaymentConditionTypeModel,
    GlobalPaymentMethodModel,
)


SEED_ACTOR = "system:payment-reference-seed"

REQUIRED_TABLES = (
    "global_payment_condition_types",
    "global_payment_methods",
)


PAYMENT_CONDITION_TYPES = (
    {
        "code": "CASH",
        "name": "Contado",
        "description": (
            "El pago se realiza de contado, sin utilizar condiciones "
            "de crédito o financiación."
        ),
        "status": "ACTIVE",
    },
    {
        "code": "CREDIT",
        "name": "Crédito",
        "description": (
            "El pago se realiza bajo condiciones de crédito acordadas."
        ),
        "status": "ACTIVE",
    },
    {
        "code": "FINANCING",
        "name": "Financiación",
        "description": (
            "El pago se realiza mediante un esquema de financiación."
        ),
        "status": "ACTIVE",
    },
)


PAYMENT_METHODS = (
    {
        "code": "CASH",
        "name": "Efectivo",
        "method_type": "CASH",
        "requires_reference": False,
        "status": "ACTIVE",
    },
    {
        "code": "BANK_TRANSFER",
        "name": "Transferencia bancaria",
        "method_type": "BANK",
        "requires_reference": True,
        "status": "ACTIVE",
    },
    {
        "code": "DEBIT_CARD",
        "name": "Tarjeta de débito",
        "method_type": "CARD",
        "requires_reference": True,
        "status": "ACTIVE",
    },
    {
        "code": "CREDIT_CARD",
        "name": "Tarjeta de crédito",
        "method_type": "CARD",
        "requires_reference": True,
        "status": "ACTIVE",
    },
    {
        "code": "DIGITAL_WALLET",
        "name": "Billetera digital",
        "method_type": "WALLET",
        "requires_reference": True,
        "status": "ACTIVE",
    },
    {
        "code": "CHECK",
        "name": "Cheque",
        "method_type": "CHECK",
        "requires_reference": True,
        "status": "ACTIVE",
    },
    {
        "code": "OTHER",
        "name": "Otro",
        "method_type": "OTHER",
        "requires_reference": False,
        "status": "ACTIVE",
    },
)


def prepare_seed() -> None:
    """Comprueba que PostgreSQL está preparado para ejecutar el seed.

    Valida la conexión y verifica que las tablas funcionales requeridas
    hayan sido creadas previamente mediante Alembic.

    Raises:
        RuntimeError: Si PostgreSQL no responde o falta alguna tabla.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

            inspector = inspect(connection)

            missing_tables = [
                table_name
                for table_name in REQUIRED_TABLES
                if not inspector.has_table(table_name)
            ]

    except SQLAlchemyError as exc:
        raise RuntimeError(
            "No fue posible conectar con PostgreSQL."
        ) from exc

    if missing_tables:
        missing = ", ".join(missing_tables)

        raise RuntimeError(
            "La base de datos no está preparada. "
            f"Faltan las tablas: {missing}. "
            "Ejecute primero las migraciones Alembic."
        )


def load_seed() -> None:
    """Carga los catálogos iniciales de manera idempotente.

    Los registros existentes se identifican por `code` y se conservan.
    Solamente se insertan códigos que todavía no existen.

    Raises:
        RuntimeError: Si ocurre un error de persistencia.
    """
    prepare_seed()

    now = datetime.now(timezone.utc)

    inserted_condition_types = 0
    skipped_condition_types = 0

    inserted_payment_methods = 0
    skipped_payment_methods = 0

    with SessionLocal() as session:
        try:
            for item in PAYMENT_CONDITION_TYPES:
                existing_id = session.scalar(
                    select(GlobalPaymentConditionTypeModel.id).where(
                        GlobalPaymentConditionTypeModel.code
                        == item["code"]
                    )
                )

                if existing_id is not None:
                    skipped_condition_types += 1
                    continue

                session.add(
                    GlobalPaymentConditionTypeModel(
                        id=uuid4(),
                        code=item["code"],
                        name=item["name"],
                        description=item["description"],
                        status=item["status"],
                        created_by=SEED_ACTOR,
                        updated_by=SEED_ACTOR,
                        created_at=now,
                        updated_at=now,
                    )
                )

                inserted_condition_types += 1

            for item in PAYMENT_METHODS:
                existing_id = session.scalar(
                    select(GlobalPaymentMethodModel.id).where(
                        GlobalPaymentMethodModel.code
                        == item["code"]
                    )
                )

                if existing_id is not None:
                    skipped_payment_methods += 1
                    continue

                session.add(
                    GlobalPaymentMethodModel(
                        id=uuid4(),
                        code=item["code"],
                        name=item["name"],
                        method_type=item["method_type"],
                        requires_reference=item[
                            "requires_reference"
                        ],
                        status=item["status"],
                        created_by=SEED_ACTOR,
                        updated_by=SEED_ACTOR,
                        created_at=now,
                        updated_at=now,
                    )
                )

                inserted_payment_methods += 1

            session.commit()

        except SQLAlchemyError as exc:
            session.rollback()

            raise RuntimeError(
                "No fue posible cargar los datos iniciales."
            ) from exc

    print("Carga de datos iniciales finalizada.")
    print(
        "Tipos de condición de pago: "
        f"{inserted_condition_types} creados, "
        f"{skipped_condition_types} existentes."
    )
    print(
        "Métodos de pago: "
        f"{inserted_payment_methods} creados, "
        f"{skipped_payment_methods} existentes."
    )


def _build_parser() -> argparse.ArgumentParser:
    """Construye el parser de comandos del proceso de seed.

    Returns:
        Parser configurado con los comandos disponibles.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Administración de datos iniciales de "
            "Payment Reference Service."
        )
    )

    parser.add_argument(
        "command",
        choices=("prepare", "load"),
        help=(
            "'prepare' valida la base de datos; "
            "'load' carga los catálogos iniciales."
        ),
    )

    return parser


def main() -> int:
    """Ejecuta el comando solicitado desde la línea de comandos.

    Returns:
        Código cero cuando el proceso finaliza correctamente o uno si
        ocurre un error funcional.
    """
    parser = _build_parser()
    args = parser.parse_args()

    try:
        if args.command == "prepare":
            prepare_seed()
            print(
                "La base de datos está preparada para cargar "
                "los datos iniciales."
            )
            return 0

        load_seed()
        return 0

    except RuntimeError as exc:
        print(
            f"Error: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())