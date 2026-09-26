"""Crea companies y branches (Fase A).

Revision ID: 0001
Revises:
Create Date: 2026-09-26

Referencias a Party Identity y Geography como UUID sin FK física
(Principio II). Única FK interna: branches.company_id → companies.id.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _location_and_audit_columns() -> list[sa.Column]:
    return [
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("address_line", sa.Text(), nullable=True),
        sa.Column("country_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("administrative_division_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("city_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
    ]


def _location_checks(table: str) -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name=op.f(f"ck_{table}_status")),
        sa.CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)",
            name=op.f(f"ck_{table}_coordinates_pair"),
        ),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name=op.f(f"ck_{table}_latitude_range")),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name=op.f(f"ck_{table}_longitude_range"),
        ),
        sa.CheckConstraint(
            "(administrative_division_id IS NULL AND city_id IS NULL) "
            "OR country_id IS NOT NULL",
            name=op.f(f"ck_{table}_geography_parent"),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "timezone",
            sa.String(60),
            nullable=False,
            server_default=sa.text("'America/Bogota'"),
        ),
        sa.Column(
            "default_currency",
            sa.CHAR(3),
            nullable=False,
            server_default=sa.text("'COP'"),
        ),
        *_location_and_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_companies"),
        sa.UniqueConstraint(
            "organization_identity_id",
            name="uq_companies_organization_identity_id",
        ),
        *_location_checks("companies"),
        sa.CheckConstraint(
            "default_currency ~ '^[A-Z]{3}$'",
            name=op.f("ck_companies_default_currency_format"),
        ),
        sa.CheckConstraint("btrim(timezone) <> ''", name=op.f("ck_companies_timezone_not_blank")),
    )
    op.create_index("ix_companies_status", "companies", ["status"])
    op.create_index("ix_companies_country_id", "companies", ["country_id"])
    op.create_index("ix_companies_city_id", "companies", ["city_id"])

    op.create_table(
        "branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("timezone", sa.String(60), nullable=True),
        *_location_and_audit_columns(),
        sa.PrimaryKeyConstraint("id", name="pk_branches"),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_branches_company_id_companies",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("company_id", "code", name="uq_branches_company_id_code"),
        *_location_checks("branches"),
        sa.CheckConstraint(
            "code = upper(btrim(code)) AND code <> ''",
            name=op.f("ck_branches_code_normalized"),
        ),
        sa.CheckConstraint(
            "timezone IS NULL OR btrim(timezone) <> ''",
            name=op.f("ck_branches_timezone_not_blank"),
        ),
    )
    op.create_index("ix_branches_company_id_status", "branches", ["company_id", "status"])
    op.create_index("ix_branches_city_id", "branches", ["city_id"])


def downgrade() -> None:
    op.drop_index("ix_branches_city_id", table_name="branches")
    op.drop_index("ix_branches_company_id_status", table_name="branches")
    op.drop_table("branches")
    op.drop_index("ix_companies_city_id", table_name="companies")
    op.drop_index("ix_companies_country_id", table_name="companies")
    op.drop_index("ix_companies_status", table_name="companies")
    op.drop_table("companies")
