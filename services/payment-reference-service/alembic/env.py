"""Configuración de Alembic para Payment Reference Service."""

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

# ============================================================
# CARGA DEL ENTORNO
# ============================================================

SERVICE_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(SERVICE_ROOT / ".env")


# IMPORTANTE:
# Estos imports deben ocurrir después de load_dotenv(), porque
# database.py carga Settings y necesita DATABASE_URL.
from payment_reference_service.config import load_settings  # noqa: E402
from payment_reference_service.infrastructure import models  # noqa: E402,F401
from payment_reference_service.infrastructure.database import Base  # noqa: E402


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = load_settings()

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecuta migraciones sin establecer una conexión activa."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones utilizando una conexión PostgreSQL activa."""
    connectable = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()