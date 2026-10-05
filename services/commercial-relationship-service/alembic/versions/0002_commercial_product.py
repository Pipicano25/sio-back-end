"""Crea las entidades de la Fase B: presentaciones, productos de proveedor, condiciones y precios.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05

`specs/010-commercial-relationship-commercial-product/data-model.md` (R-02, R-03,
R-05, R-15): cinco entidades de dominio con auditoría y `version`; FK internas
compuestas con `company_id` (misma empresa); predeterminadas como índices únicos
parciales; no solapamiento de vigencias de precios con una restricción de
exclusión (`btree_gist`). Las únicas referencias externas son `UUID REF` sin FK.
Las tablas de la Fase A solo reciben `UNIQUE (id, company_id)` para las FK
compuestas, sin cambio funcional. Sin datos iniciales.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NIL_UUID = "'00000000-0000-0000-0000-000000000000'::uuid"
NO_PRESENTATION = f"COALESCE(company_product_presentation_id, {NIL_UUID})"


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
    ]


def _status_check(table: str) -> sa.CheckConstraint:
    return sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f(f"ck_{table}_status"))


def _currency_check(table: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "currency_code ~ '^[A-Z]{3}$'", name=op.f(f"ck_{table}_currency_code_format")
    )


def _fk(name: str, columns: list[str], table: str, referred: list[str]) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        columns,
        [f"{table}.{column}" for column in referred],
        name=op.f(name),
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_unique_constraint(
        op.f("uq_company_products_id_company_id"), "company_products", ["id", "company_id"]
    )
    op.create_unique_constraint(
        op.f("uq_company_suppliers_id_company_id"), "company_suppliers", ["id", "company_id"]
    )

    # ------------------------------------------------ company_product_presentations
    table = "company_product_presentations"
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("company_product_id", sa.Uuid(), nullable=False),
        sa.Column("global_product_presentation_id", sa.Uuid(), nullable=False),
        sa.Column("internal_code", sa.String(80), nullable=True),
        sa.Column("sku", sa.String(80), nullable=True),
        sa.Column("reference_code", sa.String(100), nullable=True),
        sa.Column("is_purchasable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_sellable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_default_purchase", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_default_sale", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        _fk(
            "fk_company_product_presentations_company_product",
            ["company_product_id", "company_id"],
            "company_products",
            ["id", "company_id"],
        ),
        sa.UniqueConstraint("id", "company_id", name=op.f(f"uq_{table}_id_company_id")),
        sa.UniqueConstraint("id", "company_product_id", name=op.f(f"uq_{table}_id_company_product_id")),
        sa.UniqueConstraint(
            "company_product_id",
            "global_product_presentation_id",
            name=op.f(f"uq_{table}_product_global_presentation"),
        ),
        _status_check(table),
        sa.CheckConstraint(
            "NOT is_default_purchase OR is_purchasable",
            name=op.f(f"ck_{table}_default_purchase_purchasable"),
        ),
        sa.CheckConstraint(
            "NOT is_default_sale OR is_sellable",
            name=op.f(f"ck_{table}_default_sale_sellable"),
        ),
        sa.CheckConstraint(
            "status = 'ACTIVE' OR (NOT is_default_purchase AND NOT is_default_sale)",
            name=op.f(f"ck_{table}_default_requires_active"),
        ),
        sa.CheckConstraint(
            "(sku IS NULL OR (sku = btrim(sku) AND sku <> '')) AND "
            "(internal_code IS NULL OR (internal_code = btrim(internal_code) AND internal_code <> ''))",
            name=op.f(f"ck_{table}_codes_not_blank"),
        ),
    )
    op.create_index(
        op.f(f"uq_{table}_company_id_sku_ci"),
        table,
        ["company_id", sa.text("lower(sku)")],
        unique=True,
        postgresql_where=sa.text("sku IS NOT NULL"),
    )
    op.create_index(
        op.f(f"uq_{table}_company_id_internal_code_ci"),
        table,
        ["company_id", sa.text("lower(internal_code)")],
        unique=True,
        postgresql_where=sa.text("internal_code IS NOT NULL"),
    )
    op.create_index(
        op.f(f"uq_{table}_default_purchase"),
        table,
        ["company_product_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND is_default_purchase"),
    )
    op.create_index(
        op.f(f"uq_{table}_default_sale"),
        table,
        ["company_product_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND is_default_sale"),
    )
    op.create_index(op.f(f"ix_{table}_company_id_status"), table, ["company_id", "status"])
    op.create_index(
        op.f(f"ix_{table}_global_product_presentation_id"), table, ["global_product_presentation_id"]
    )

    # ------------------------------------------------------------- supplier_products
    table = "supplier_products"
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("company_supplier_id", sa.Uuid(), nullable=False),
        sa.Column("company_product_id", sa.Uuid(), nullable=False),
        sa.Column("company_product_presentation_id", sa.Uuid(), nullable=True),
        sa.Column("supplier_product_code", sa.String(100), nullable=True),
        sa.Column("purchase_unit_id", sa.Uuid(), nullable=False),
        sa.Column("minimum_order_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("pack_quantity", sa.Numeric(18, 4), nullable=False, server_default="1"),
        sa.Column("negotiated_unit_cost", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency_code", sa.CHAR(3), nullable=False),
        sa.Column("expected_supplier_lead_time_hours", sa.Numeric(12, 2), nullable=True),
        sa.Column("priority", sa.SmallInteger(), nullable=True),
        sa.Column("is_preferred", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        _fk(
            "fk_supplier_products_company_supplier",
            ["company_supplier_id", "company_id"],
            "company_suppliers",
            ["id", "company_id"],
        ),
        _fk(
            "fk_supplier_products_company_product",
            ["company_product_id", "company_id"],
            "company_products",
            ["id", "company_id"],
        ),
        _fk(
            "fk_supplier_products_presentation",
            ["company_product_presentation_id", "company_product_id"],
            "company_product_presentations",
            ["id", "company_product_id"],
        ),
        _status_check(table),
        _currency_check(table),
        sa.CheckConstraint(
            "minimum_order_quantity >= 0 AND pack_quantity > 0",
            name=op.f(f"ck_{table}_quantities"),
        ),
        sa.CheckConstraint(
            "(negotiated_unit_cost IS NULL OR negotiated_unit_cost >= 0) AND "
            "(expected_supplier_lead_time_hours IS NULL OR expected_supplier_lead_time_hours >= 0) AND "
            "(priority IS NULL OR priority >= 0)",
            name=op.f(f"ck_{table}_non_negative"),
        ),
        sa.CheckConstraint(
            "status = 'ACTIVE' OR NOT is_preferred",
            name=op.f(f"ck_{table}_preferred_requires_active"),
        ),
    )
    op.create_index(
        op.f(f"uq_{table}_active_relation"),
        table,
        ["company_supplier_id", "company_product_id", sa.text(NO_PRESENTATION)],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        op.f(f"uq_{table}_preferred"),
        table,
        ["company_product_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND is_preferred"),
    )
    op.create_index(op.f(f"ix_{table}_company_id_status"), table, ["company_id", "status"])
    op.create_index(op.f(f"ix_{table}_company_product_id"), table, ["company_product_id"])
    op.create_index(op.f(f"ix_{table}_company_supplier_id"), table, ["company_supplier_id"])

    # --------------------------------------------------- supplier_payment_conditions
    table = "supplier_payment_conditions"
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("company_supplier_id", sa.Uuid(), nullable=False),
        sa.Column("payment_condition_type_id", sa.Uuid(), nullable=False),
        sa.Column("currency_code", sa.CHAR(3), nullable=False),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credit_limit", sa.Numeric(18, 2), nullable=True),
        sa.Column("interest_rate_percentage", sa.Numeric(7, 4), nullable=True),
        sa.Column("cash_discount_percentage", sa.Numeric(7, 4), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        _fk(
            "fk_supplier_payment_conditions_company_supplier",
            ["company_supplier_id", "company_id"],
            "company_suppliers",
            ["id", "company_id"],
        ),
        _status_check(table),
        _currency_check(table),
        sa.CheckConstraint(
            "payment_terms_days BETWEEN 0 AND 3650", name=op.f(f"ck_{table}_terms_range")
        ),
        sa.CheckConstraint(
            "(credit_limit IS NULL OR credit_limit >= 0) AND "
            "(interest_rate_percentage IS NULL OR interest_rate_percentage BETWEEN 0 AND 100) AND "
            "(cash_discount_percentage IS NULL OR cash_discount_percentage BETWEEN 0 AND 100)",
            name=op.f(f"ck_{table}_amounts"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from", name=op.f(f"ck_{table}_validity")
        ),
        sa.CheckConstraint(
            "status = 'ACTIVE' OR NOT is_default",
            name=op.f(f"ck_{table}_default_requires_active"),
        ),
    )
    op.create_index(
        op.f(f"uq_{table}_default"),
        table,
        ["company_supplier_id", "currency_code"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND is_default"),
    )
    op.create_index(op.f(f"ix_{table}_company_supplier_id"), table, ["company_supplier_id"])
    op.create_index(
        op.f(f"ix_{table}_payment_condition_type_id"), table, ["payment_condition_type_id"]
    )

    # ---------------------------------------------------------------- price_lists
    table = "price_lists"
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("currency_code", sa.CHAR(3), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        sa.UniqueConstraint("id", "company_id", name=op.f(f"uq_{table}_id_company_id")),
        _status_check(table),
        _currency_check(table),
        sa.CheckConstraint(
            "valid_from IS NULL OR valid_to IS NULL OR valid_to > valid_from",
            name=op.f(f"ck_{table}_validity"),
        ),
        sa.CheckConstraint(
            "status = 'ACTIVE' OR NOT is_default",
            name=op.f(f"ck_{table}_default_requires_active"),
        ),
        sa.CheckConstraint(
            "code = btrim(code) AND code <> ''", name=op.f(f"ck_{table}_code_not_blank")
        ),
        sa.CheckConstraint("btrim(name) <> ''", name=op.f(f"ck_{table}_name_not_blank")),
    )
    op.create_index(
        op.f(f"uq_{table}_company_id_code_ci"),
        table,
        ["company_id", sa.text("lower(code)")],
        unique=True,
    )
    op.create_index(
        op.f(f"uq_{table}_default"),
        table,
        ["company_id", "currency_code"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND is_default"),
    )
    op.create_index(op.f(f"ix_{table}_company_id_status"), table, ["company_id", "status"])

    # ------------------------------------------------------------ price_list_items
    table = "price_list_items"
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("price_list_id", sa.Uuid(), nullable=False),
        sa.Column("company_product_id", sa.Uuid(), nullable=False),
        sa.Column("company_product_presentation_id", sa.Uuid(), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        _fk(
            "fk_price_list_items_price_list",
            ["price_list_id", "company_id"],
            "price_lists",
            ["id", "company_id"],
        ),
        _fk(
            "fk_price_list_items_company_product",
            ["company_product_id", "company_id"],
            "company_products",
            ["id", "company_id"],
        ),
        _fk(
            "fk_price_list_items_presentation",
            ["company_product_presentation_id", "company_product_id"],
            "company_product_presentations",
            ["id", "company_product_id"],
        ),
        _status_check(table),
        sa.CheckConstraint("unit_price >= 0", name=op.f(f"ck_{table}_unit_price_non_negative")),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from", name=op.f(f"ck_{table}_validity")
        ),
    )
    op.execute(
        "ALTER TABLE price_list_items ADD CONSTRAINT ex_price_list_items_no_overlap "
        "EXCLUDE USING gist ("
        "price_list_id WITH =, "
        "company_product_id WITH =, "
        f"({NO_PRESENTATION}) WITH =, "
        "tstzrange(valid_from, valid_to, '[)') WITH &&"
        ") WHERE (status = 'ACTIVE')"
    )
    op.create_index(
        op.f(f"ix_{table}_resolution"), table, ["price_list_id", "company_product_id", "valid_from"]
    )
    op.create_index(op.f(f"ix_{table}_company_id_status"), table, ["company_id", "status"])


def downgrade() -> None:
    # La extensión btree_gist se conserva: puede estar en uso por otros objetos.
    op.drop_table("price_list_items")
    op.drop_table("price_lists")
    op.drop_table("supplier_payment_conditions")
    op.drop_table("supplier_products")
    op.drop_table("company_product_presentations")
    op.drop_constraint(op.f("uq_company_suppliers_id_company_id"), "company_suppliers", type_="unique")
    op.drop_constraint(op.f("uq_company_products_id_company_id"), "company_products", type_="unique")
