"""create contact profiles (Fase B)

Perfiles de contacto versionados de personas y organizaciones (estándar 4.11 y
4.13; data-model tabla 2). Geografía y contexto de confirmación son `UUID REF`
sin FK (Principio II).

Revision ID: 0014_create_contact_profiles
Revises: 0013_create_business_sectors
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0014_create_contact_profiles"
down_revision: Union[str, Sequence[str], None] = "0013_create_business_sectors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROFILE_TABLES = (
    ("person_contact_profiles", "person_identity_id", "person_identities"),
    ("organization_contact_profiles", "organization_identity_id", "organization_identities"),
)


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
    for table, owner_column, owner_table in PROFILE_TABLES:
        op.create_table(
            table,
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(owner_column, postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.String(length=254), nullable=True),
            sa.Column("phone", sa.String(length=40), nullable=True),
            sa.Column("address_line", sa.Text(), nullable=True),
            sa.Column("country_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("administrative_division_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("postal_code", sa.String(length=20), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
            sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("confirmed_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("confirmed_by_company_id", postgresql.UUID(as_uuid=True), nullable=False),
            *_audit_columns(),
            sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
            sa.ForeignKeyConstraint(
                [owner_column],
                [f"{owner_table}.id"],
                name=f"fk_{table}_{owner_column}",
            ),
            sa.CheckConstraint(
                "email IS NOT NULL OR phone IS NOT NULL OR address_line IS NOT NULL",
                name=f"ck_{table}_has_contact",
            ),
            sa.CheckConstraint(
                "(is_active AND valid_to IS NULL) OR (NOT is_active AND valid_to IS NOT NULL)",
                name=f"ck_{table}_validity",
            ),
            sa.CheckConstraint(
                "valid_to IS NULL OR valid_to >= valid_from",
                name=f"ck_{table}_validity_range",
            ),
            sa.CheckConstraint(
                "(administrative_division_id IS NULL OR country_id IS NOT NULL) "
                "AND (city_id IS NULL OR country_id IS NOT NULL)",
                name=f"ck_{table}_geography_parent",
            ),
        )
        op.create_index(
            f"uq_{table}_active",
            table,
            [owner_column],
            unique=True,
            postgresql_where=sa.text("is_active"),
        )
        op.create_index(
            f"ix_{table}_owner_valid_from",
            table,
            [owner_column, sa.text("valid_from DESC")],
        )
        op.create_index(
            f"ix_{table}_confirmed_by_company",
            table,
            ["confirmed_by_company_id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table, _, _ in reversed(PROFILE_TABLES):
        op.drop_table(table)
