"""Crea company_products, company_customers y company_suppliers (Fase A).

Revision ID: 0001
Revises:
Create Date: 2026-10-03

`specs/007-commercial-relationship-core/data-model.md`: tres entidades de
dominio con auditoría y `version`, restricciones e índices nombrados y sin FK
físicas (todas las referencias son `UUID REF`). Sin datos iniciales.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
    ]


def _code_and_name_checks(table: str) -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint(
            "internal_code = btrim(internal_code) AND internal_code <> ''",
            name=op.f(f"ck_{table}_internal_code_not_blank"),
        ),
        sa.CheckConstraint(
            "btrim(display_name) <> ''",
            name=op.f(f"ck_{table}_display_name_not_blank"),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "company_products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("global_product_id", sa.Uuid(), nullable=False),
        sa.Column("internal_code", sa.String(60), nullable=False),
        sa.Column("reference_code", sa.String(100), nullable=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("short_name", sa.String(160), nullable=True),
        sa.Column("sale_price", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency_code", sa.CHAR(3), nullable=False),
        sa.Column("reference_cost", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("inventory_control_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("lot_tracking_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expiration_tracking_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_purchasable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_sellable", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_products")),
        sa.UniqueConstraint(
            "company_id",
            "global_product_id",
            name=op.f("uq_company_products_company_id_global_product_id"),
        ),
        sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f("ck_company_products_status")),
        sa.CheckConstraint("sale_price >= 0", name=op.f("ck_company_products_sale_price_non_negative")),
        sa.CheckConstraint(
            "reference_cost >= 0", name=op.f("ck_company_products_reference_cost_non_negative")
        ),
        sa.CheckConstraint(
            "currency_code ~ '^[A-Z]{3}$'", name=op.f("ck_company_products_currency_code_format")
        ),
        sa.CheckConstraint(
            "NOT lot_tracking_enabled OR inventory_control_enabled",
            name=op.f("ck_company_products_lot_requires_inventory"),
        ),
        sa.CheckConstraint(
            "NOT expiration_tracking_enabled OR lot_tracking_enabled",
            name=op.f("ck_company_products_expiration_requires_lot"),
        ),
        *_code_and_name_checks("company_products"),
    )
    op.create_index(
        op.f("uq_company_products_company_id_internal_code_ci"),
        "company_products",
        ["company_id", sa.text("lower(internal_code)")],
        unique=True,
    )
    op.create_index(
        op.f("ix_company_products_company_id_status"), "company_products", ["company_id", "status"]
    )
    op.create_index(
        op.f("ix_company_products_global_product_id"), "company_products", ["global_product_id"]
    )

    op.create_table(
        "company_customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("customer_kind", sa.String(20), nullable=False),
        sa.Column("person_identity_id", sa.Uuid(), nullable=True),
        sa.Column("organization_identity_id", sa.Uuid(), nullable=True),
        sa.Column("internal_code", sa.String(60), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("preferred_contact_person_id", sa.Uuid(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_customers")),
        sa.CheckConstraint(
            "customer_kind IN ('PERSON','ORGANIZATION')", name=op.f("ck_company_customers_kind")
        ),
        sa.CheckConstraint(
            "(customer_kind = 'PERSON' AND person_identity_id IS NOT NULL "
            "AND organization_identity_id IS NULL) OR "
            "(customer_kind = 'ORGANIZATION' AND organization_identity_id IS NOT NULL "
            "AND person_identity_id IS NULL)",
            name=op.f("ck_company_customers_identity_by_kind"),
        ),
        sa.CheckConstraint(
            "preferred_contact_person_id IS NULL OR customer_kind = 'ORGANIZATION'",
            name=op.f("ck_company_customers_contact_only_organization"),
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE')", name=op.f("ck_company_customers_status")
        ),
        *_code_and_name_checks("company_customers"),
    )
    op.create_index(
        op.f("uq_company_customers_company_id_person_identity_id"),
        "company_customers",
        ["company_id", "person_identity_id"],
        unique=True,
        postgresql_where=sa.text("person_identity_id IS NOT NULL"),
    )
    op.create_index(
        op.f("uq_company_customers_company_id_organization_identity_id"),
        "company_customers",
        ["company_id", "organization_identity_id"],
        unique=True,
        postgresql_where=sa.text("organization_identity_id IS NOT NULL"),
    )
    op.create_index(
        op.f("uq_company_customers_company_id_internal_code_ci"),
        "company_customers",
        ["company_id", sa.text("lower(internal_code)")],
        unique=True,
    )
    op.create_index(
        op.f("ix_company_customers_company_id_status"), "company_customers", ["company_id", "status"]
    )
    op.create_index(
        op.f("ix_company_customers_person_identity_id"), "company_customers", ["person_identity_id"]
    )
    op.create_index(
        op.f("ix_company_customers_organization_identity_id"),
        "company_customers",
        ["organization_identity_id"],
    )

    op.create_table(
        "company_suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("organization_identity_id", sa.Uuid(), nullable=False),
        sa.Column("internal_code", sa.String(60), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("preferred_contact_person_id", sa.Uuid(), nullable=True),
        sa.Column("block_reason", sa.String(500), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_suppliers")),
        sa.UniqueConstraint(
            "company_id",
            "organization_identity_id",
            name=op.f("uq_company_suppliers_company_id_organization_identity_id"),
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE','BLOCKED')", name=op.f("ck_company_suppliers_status")
        ),
        sa.CheckConstraint(
            "(status = 'BLOCKED' AND block_reason IS NOT NULL AND btrim(block_reason) <> '') "
            "OR (status <> 'BLOCKED' AND block_reason IS NULL)",
            name=op.f("ck_company_suppliers_block_reason_consistency"),
        ),
        *_code_and_name_checks("company_suppliers"),
    )
    op.create_index(
        op.f("uq_company_suppliers_company_id_internal_code_ci"),
        "company_suppliers",
        ["company_id", sa.text("lower(internal_code)")],
        unique=True,
    )
    op.create_index(
        op.f("ix_company_suppliers_company_id_status"), "company_suppliers", ["company_id", "status"]
    )
    op.create_index(
        op.f("ix_company_suppliers_organization_identity_id"),
        "company_suppliers",
        ["organization_identity_id"],
    )


def downgrade() -> None:
    op.drop_table("company_suppliers")
    op.drop_table("company_customers")
    op.drop_table("company_products")
