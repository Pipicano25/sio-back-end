"""create global business sectors (Fase B)

Catálogo global y jerárquico de sectores económicos (estándar 4.7; data-model
tabla 1). Los datos iniciales (CIIU_REV4_AC) se cargan con el módulo `seed`,
nunca con migraciones (D2).

Revision ID: 0013_create_business_sectors
Revises: 0012_audit_actor_as_text
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0013_create_business_sectors"
down_revision: Union[str, Sequence[str], None] = "0012_audit_actor_as_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list[sa.Column]:
    """Auditoría (Principio VI, D1) y control de concurrencia (Principio VII)."""
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
        "global_business_sectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_sector_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("classification_system", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'ACTIVE'"), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_global_business_sectors"),
        sa.ForeignKeyConstraint(
            ["parent_sector_id"],
            ["global_business_sectors.id"],
            name="fk_global_business_sectors_parent_sector_id",
        ),
        sa.UniqueConstraint(
            "classification_system",
            "code",
            name="uq_global_business_sectors_system_code",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_global_business_sectors_status",
        ),
        sa.CheckConstraint(
            "parent_sector_id IS NULL OR parent_sector_id <> id",
            name="ck_global_business_sectors_not_self_parent",
        ),
    )
    op.create_index("ix_global_business_sectors_parent", "global_business_sectors", ["parent_sector_id"])
    op.create_index("ix_global_business_sectors_status", "global_business_sectors", ["status"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("global_business_sectors")
