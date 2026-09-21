"""create organization identities

Revision ID: 0008_create_org_identities
Revises: 0007_relax_id_codes
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0008_create_org_identities"
down_revision: Union[str, Sequence[str], None] = "0007_relax_id_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "organization_identities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "country_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "identification_type",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "identification_number",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "verification_digit",
            sa.String(length=5),
            nullable=True,
        ),
        sa.Column(
            "legal_name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "trade_name",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "organization_type",
            sa.String(length=40),
            nullable=True,
        ),
        sa.Column(
            "registration_status",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "website",
            sa.String(length=300),
            nullable=True,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "country_id",
            "identification_type",
            "identification_number",
            name="uq_organization_identities_identification",
        ),
    )
    op.create_index(
        "ix_organization_identities_country_id",
        "organization_identities",
        ["country_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_identities_identification_type",
        "organization_identities",
        ["identification_type"],
        unique=False,
    )
    op.create_index(
        "ix_organization_identities_registration_status",
        "organization_identities",
        ["registration_status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_organization_identities_registration_status",
        table_name="organization_identities",
    )
    op.drop_index(
        "ix_organization_identities_identification_type",
        table_name="organization_identities",
    )
    op.drop_index(
        "ix_organization_identities_country_id",
        table_name="organization_identities",
    )
    op.drop_table(
        "organization_identities",
    )
