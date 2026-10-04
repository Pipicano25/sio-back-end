"""Configuración de entorno Alembic para Commercial Relationship Service."""

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from commercial_relationship_service.config import load_settings
from commercial_relationship_service.infrastructure import models  # noqa: F401
from commercial_relationship_service.infrastructure.database import Base

load_dotenv(override=False)

settings = load_settings()

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecuta migraciones sin conexión directa a la base de datos."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones conectándose a PostgreSQL."""
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)

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
