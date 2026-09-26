"""Convierte created_by/updated_by a texto (D1).

Revision ID: 0012_audit_actor_as_text
Revises: 0011_add_identity_status
Create Date: 2026-09-25

La Constitución (Principio VI, D1) exige `String(255)` con el `sub` de la
identidad autenticada, que no siempre es un UUID (cuentas de servicio, actor
técnico del `seed`). La conversión conserva los valores existentes.

El `downgrade` solo es posible mientras todos los valores sean UUID; si hay
otros (p. ej. `system:party-identity-seed`), falla con un mensaje explícito.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0012_audit_actor_as_text"
down_revision: Union[str, Sequence[str], None] = "0011_add_identity_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "identification_type_rules",
    "person_identities",
    "organization_identities",
)
COLUMNS = (
    "created_by",
    "updated_by",
)
UUID_PATTERN = (
    "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    "[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        for column in COLUMNS:
            op.alter_column(
                table,
                column,
                type_=sa.String(length=255),
                existing_nullable=False,
                postgresql_using=f"{column}::text",
            )


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()

    for table in TABLES:
        for column in COLUMNS:
            invalid = connection.execute(
                sa.text(
                    f"SELECT count(*) FROM {table} "
                    f"WHERE {column} !~ :pattern"
                ),
                {"pattern": UUID_PATTERN},
            ).scalar_one()

            if invalid:
                raise RuntimeError(
                    f"No es posible revertir {table}.{column} a UUID: "
                    f"{invalid} fila(s) contienen identidades que no son UUID."
                )

    for table in TABLES:
        for column in COLUMNS:
            op.alter_column(
                table,
                column,
                type_=postgresql.UUID(as_uuid=True),
                existing_nullable=False,
                postgresql_using=f"{column}::uuid",
            )
