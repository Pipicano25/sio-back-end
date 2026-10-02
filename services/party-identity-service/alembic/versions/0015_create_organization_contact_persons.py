"""create organization contact persons (Fase B)

Personas de contacto de una organización (estándar 4.14; data-model tabla 3).
Se añaden auditoría y `version`, ausentes en el estándar (C-01, C-03).

Revision ID: 0015_create_contact_persons
Revises: 0014_create_contact_profiles
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0015_create_contact_persons"
down_revision: Union[str, Sequence[str], None] = "0014_create_contact_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "organization_contact_persons"


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
        sa.Column("person_identity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("position", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
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
            "email IS NOT NULL OR phone IS NOT NULL OR person_identity_id IS NOT NULL",
            name=f"ck_{TABLE}_has_contact",
        ),
        sa.CheckConstraint(
            "NOT is_primary OR is_active",
            name=f"ck_{TABLE}_primary_active",
        ),
    )
    op.create_index(
        f"uq_{TABLE}_primary",
        TABLE,
        ["organization_identity_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND is_primary"),
    )
    op.create_index(
        f"uq_{TABLE}_person",
        TABLE,
        ["organization_identity_id", "person_identity_id"],
        unique=True,
        postgresql_where=sa.text("is_active AND person_identity_id IS NOT NULL"),
    )
    op.create_index(f"ix_{TABLE}_org", TABLE, ["organization_identity_id", "is_active"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table(TABLE)
