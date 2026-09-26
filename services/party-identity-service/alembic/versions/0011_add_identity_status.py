"""Agrega el estado de uso a personas y organizaciones.

Revision ID: 0011_add_identity_status
Revises: 0010_org_nit_rule_no_dv
Create Date: 2026-09-25

`status` (`ACTIVE`/`INACTIVE`) es el estado de uso (D7, DS-02),
independiente de `verification_status` y de `registration_status`. Las filas
existentes quedan `ACTIVE` por el valor por defecto.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0011_add_identity_status"
down_revision: Union[str, Sequence[str], None] = "0010_org_nit_rule_no_dv"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "person_identities",
    "organization_identities",
)


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'ACTIVE'"),
            ),
        )
        op.create_check_constraint(
            f"ck_{table}_status",
            table,
            "status IN ('ACTIVE', 'INACTIVE')",
        )
        op.create_index(
            f"ix_{table}_status",
            table,
            ["status"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES:
        op.drop_index(
            f"ix_{table}_status",
            table_name=table,
        )
        op.drop_constraint(
            f"ck_{table}_status",
            table,
            type_="check",
        )
        op.drop_column(
            table,
            "status",
        )
