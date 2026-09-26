"""Índices sobre `global_product_id` usados como filtro en identificadores y asignaciones.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-25

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea los índices de filtro por producto (data-model §12 y §15)."""
    op.create_index(
        "ix_global_product_identifiers_global_product_id",
        "global_product_identifiers",
        ["global_product_id"],
        unique=False,
    )
    op.create_index(
        "ix_global_product_group_assignments_global_product_id",
        "global_product_group_assignments",
        ["global_product_id"],
        unique=False,
    )


def downgrade() -> None:
    """Elimina los índices de filtro por producto."""
    op.drop_index(
        "ix_global_product_group_assignments_global_product_id",
        table_name="global_product_group_assignments",
    )
    op.drop_index(
        "ix_global_product_identifiers_global_product_id",
        table_name="global_product_identifiers",
    )
