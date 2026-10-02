"""create organization business sectors (Fase B)

Sectores económicos de una organización con vigencia `[valid_from, valid_to)`
(estándar 4.15; data-model tabla 4). Se añaden auditoría y `version` (C-01).

Revision ID: 0016_create_org_business_sectors
Revises: 0015_create_contact_persons
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0016_create_org_business_sectors"
down_revision: Union[str, Sequence[str], None] = "0015_create_contact_persons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "organization_business_sectors"


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("global_business_sector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=f"pk_{TABLE}"),
        sa.ForeignKeyConstraint(
            ["organization_identity_id"],
            ["organization_identities.id"],
            name=f"fk_{TABLE}_organization_identity_id",
        ),
        sa.ForeignKeyConstraint(
            ["global_business_sector_id"],
            ["global_business_sectors.id"],
            name=f"fk_{TABLE}_global_business_sector_id",
        ),
        sa.CheckConstraint(
            "(is_active AND valid_to IS NULL) OR (NOT is_active AND valid_to IS NOT NULL)",
            name=f"ck_{TABLE}_validity",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name=f"ck_{TABLE}_validity_range",
        ),
        sa.CheckConstraint(
            "NOT is_primary OR is_active",
            name=f"ck_{TABLE}_primary_active",
        ),
    )
    op.create_index(
        f"uq_{TABLE}_active",
        TABLE,
        ["organization_identity_id", "global_business_sector_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        f"uq_{TABLE}_primary",
        TABLE,
        ["organization_identity_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND is_primary"),
    )
    op.create_index(f"ix_{TABLE}_org", TABLE, ["organization_identity_id", "is_active"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table(TABLE)
