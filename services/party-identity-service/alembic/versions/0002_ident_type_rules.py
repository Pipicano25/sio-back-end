"""create identification type rules

Revision ID: 0002_ident_type_rules
Revises: 0001_create_person_identities
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0002_ident_type_rules"
down_revision: Union[str, Sequence[str], None] = "0001_create_person_identities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "identification_type_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "party_kind",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "country_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "identification_type",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "number_pattern",
            sa.String(length=300),
            nullable=False,
        ),
        sa.Column(
            "number_pattern_description",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "example_value",
            sa.String(length=40),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "valid_to",
            sa.DateTime(timezone=True),
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
        sa.CheckConstraint(
            "party_kind IN ('PERSON', 'ORGANIZATION')",
            name="ck_identification_type_rules_party_kind",
        ),
        sa.CheckConstraint(
            "identification_type IN "
            "('NATIONAL_ID', 'FOREIGN_ID', 'PASSPORT', "
            "'TAX_ID', 'REGISTRATION_ID', 'OTHER')",
            name="ck_identification_type_rules_identification_type",
        ),
        sa.CheckConstraint(
            "length(trim(number_pattern)) > 0",
            name="ck_identification_type_rules_number_pattern_not_empty",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_identification_type_rules_valid_range",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
    )
    op.create_index(
        "ix_identification_type_rules_country_id",
        "identification_type_rules",
        ["country_id"],
        unique=False,
    )
    op.create_index(
        "uq_identification_type_rules_active",
        "identification_type_rules",
        [
            "party_kind",
            "country_id",
            "identification_type",
        ],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_identification_type_rules_active",
        table_name="identification_type_rules",
    )
    op.drop_index(
        "ix_identification_type_rules_country_id",
        table_name="identification_type_rules",
    )
    op.drop_table(
        "identification_type_rules",
    )
