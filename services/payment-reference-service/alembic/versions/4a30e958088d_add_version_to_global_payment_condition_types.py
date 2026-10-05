"""add version to global payment condition types

Revision ID: 4a30e958088d
Revises: 1e2923297584
Create Date: 2026-10-05 00:00:00.000000

Feature 008 (FR-011, Principio VII): concurrencia optimista de
`GlobalPaymentConditionType`. Los registros existentes quedan en versión 1.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a30e958088d'
down_revision: Union[str, Sequence[str], None] = '1e2923297584'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Añade `version` (1 para las filas existentes)."""
    op.add_column(
        'global_payment_condition_types',
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    )


def downgrade() -> None:
    """Elimina `version`."""
    op.drop_column('global_payment_condition_types', 'version')
