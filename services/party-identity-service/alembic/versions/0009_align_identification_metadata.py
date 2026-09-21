"""align identification metadata

Revision ID: 0009_align_ident_metadata
Revises: 0008_create_org_identities
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0009_align_ident_metadata"
down_revision: Union[str, Sequence[str], None] = "0008_create_org_identities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "person_identities",
        "identification_type",
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "person_identities",
        "identification_type",
        existing_type=sa.String(length=40),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
