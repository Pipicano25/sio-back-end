"""Configuración de entorno Alembic para Product Catalog Service."""

import os

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from product_catalog_service.infrastructure import models  # noqa: F401
from product_catalog_service.infrastructure.database import Base


load_dotenv(
    override=False,
)


def _database_url() -> str:
    """Obtiene la URL de PostgreSQL desde el entorno."""
    value = os.getenv("DATABASE_URL")

    if value is None or not value.strip():
        raise RuntimeError(
            "La variable de entorno DATABASE_URL es obligatoria para ejecutar migraciones."
        )

    return value.strip()


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecuta migraciones sin conexión directa a la base de datos."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones conectándose a PostgreSQL."""
    connectable = create_engine(
        _database_url(),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
