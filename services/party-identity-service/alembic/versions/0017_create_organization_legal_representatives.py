"""create organization legal representatives (Fase B)

Representantes legales con vigencia `[valid_from, valid_to)` (estándar 4.16;
data-model tabla 5). `created_by_user_id` del estándar se sustituye por
`created_by`/`updated_by` texto (D1, C-02); `is_primary` se deriva de
`representative_type` (C-04).

Revision ID: 0017_create_legal_reps
Revises: 0016_create_org_business_sectors
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0017_create_legal_reps"
down_revision: Union[str, Sequence[str], None] = "0016_create_org_business_sectors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "organization_legal_representatives"


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
        sa.Column("person_identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("representative_type", sa.String(length=30), nullable=False),
        sa.Column("position", sa.String(length=120), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_document_reference", sa.String(length=1000), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=f"pk_{TABLE}"),
        sa.ForeignKeyConstraint(
            ["organization_identity_id"],
            ["organization_identities.id"],
            name=f"fk_{TABLE}_organization_identity_id",
        ),
        sa.ForeignKeyConstraint(
            ["person_identity_id"],
            ["person_identities.id"],
            name=f"fk_{TABLE}_person_identity_id",
        ),
        sa.CheckConstraint(
            "representative_type IN ('PRIMARY', 'ALTERNATE', 'OTHER')",
            name=f"ck_{TABLE}_type",
        ),
        sa.CheckConstraint(
            "is_primary = (representative_type = 'PRIMARY')",
            name=f"ck_{TABLE}_primary_flag",
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
            "source_document_reference IS NULL OR length(btrim(source_document_reference)) > 0",
            name=f"ck_{TABLE}_doc_not_blank",
        ),
    )
    op.create_index(
        f"uq_{TABLE}_primary",
        TABLE,
        ["organization_identity_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND representative_type = 'PRIMARY'"),
    )
    op.create_index(
        f"uq_{TABLE}_person",
        TABLE,
        ["organization_identity_id", "person_identity_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(f"ix_{TABLE}_org", TABLE, ["organization_identity_id", "is_active"])
    op.create_index(f"ix_{TABLE}_person", TABLE, ["person_identity_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table(TABLE)
