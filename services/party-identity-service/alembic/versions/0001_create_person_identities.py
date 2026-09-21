"""create person identities

Revision ID: 0001_create_person_identities
Revises:
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0001_create_person_identities"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "person_identities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "identification_country_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "identification_type",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "identification_number",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "first_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "middle_name",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "last_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "second_last_name",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "birth_date",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "verification_status",
            sa.String(length=20),
            nullable=False,
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
        sa.CheckConstraint(
            "identification_type IN "
            "('NATIONAL_ID', 'FOREIGN_ID', 'PASSPORT', 'TAX_ID', 'OTHER')",
            name="ck_person_identities_identification_type",
        ),
        sa.CheckConstraint(
            "verification_status IN "
            "('UNVERIFIED', 'VERIFIED', 'SUSPENDED')",
            name="ck_person_identities_verification_status",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "identification_country_id",
            "identification_type",
            "identification_number",
            name="uq_person_identities_identification",
        ),
    )
    op.create_index(
        "ix_person_identities_identification_country_id",
        "person_identities",
        ["identification_country_id"],
        unique=False,
    )
    op.create_index(
        "ix_person_identities_identification_type",
        "person_identities",
        ["identification_type"],
        unique=False,
    )
    op.create_index(
        "ix_person_identities_verification_status",
        "person_identities",
        ["verification_status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_person_identities_verification_status",
        table_name="person_identities",
    )
    op.drop_index(
        "ix_person_identities_identification_type",
        table_name="person_identities",
    )
    op.drop_index(
        "ix_person_identities_identification_country_id",
        table_name="person_identities",
    )
    op.drop_table(
        "person_identities",
    )
