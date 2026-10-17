"""Precios automáticos por recepción física de compras (spec 021).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-15

- **Políticas de precios de lista** (FR-021-01..04): `price_list_pricing_policies` (entidad de dominio con
  `version`), con el historial inmutable de su porcentaje (`price_list_pricing_policy_terms`) y de sus
  presentaciones (`price_list_pricing_policy_presentations`). Dos exclusiones GiST garantizan, también ante
  operaciones concurrentes, un solo término vigente por política y que una presentación no esté en dos
  políticas de la misma lista en el mismo instante (RC-021-1).
- **Tasa de impuesto de compra** del producto de la empresa (FR-021-07): `company_products.purchase_tax_percentage`,
  anulable (NULL = sin configurar; 0 es válido).
- **Solicitudes y aplicaciones automáticas** (FR-021-19..28): inbox idempotente
  `automatic_price_update_requests` (D26) y `automatic_price_applications`, una por lista y presentación, con la
  captura inmutable de la política vigente en la recepción (RC-021-5). Un trigger impide cambiar una aplicación en
  estado final (RC-021-10).
- **Precios de lista** (FR-021-24): `origin`, `closure_reason` (`AUTOMATIC_SUPERSEDED`) y `automatic_application_id`,
  anulables.

Metadatos adoptados (opción interina declarada en `data-model.md`): D25 para las asociaciones inmutables
(`created_at`, `created_by`, `closed_at`, `closed_by`) y D26 para el inbox (`created_at`, `created_by`).

**Datos existentes:** ninguna fila se modifica; las columnas nuevas quedan en NULL (DS-09). `downgrade` se detiene
**sin cambios** si ya existen datos de la spec 021, porque los eliminaría; hace falta una decisión humana.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICIES = "price_list_pricing_policies"
TERMS = "price_list_pricing_policy_terms"
ASSIGNMENTS = "price_list_pricing_policy_presentations"
REQUESTS = "automatic_price_update_requests"
APPLICATIONS = "automatic_price_applications"

# Ajuste del 2026-10-16 en este mismo archivo (la migración no se aplicó en ningún entorno compartido; Constitución
# §migraciones): `SKIPPED_NO_POLICY` reemplaza a `ENDED_NO_POLICY` y `NO_PRICE_TO_END`, y `NO_POLICY` deja de ser un
# motivo de cierre (RC-021-13).
FINAL_STATUSES = (
    "APPLIED",
    "UNCHANGED",
    "SKIPPED_NO_POLICY",
    "SKIPPED_LIST_NOT_EFFECTIVE",
    "SKIPPED_CURRENCY_MISMATCH",
    "SKIPPED_PRESENTATION_INACTIVE",
    "SKIPPED_ZERO_COST",
    "RESOLVED",
)
STATUSES = ("PENDING", "FAILED", *FINAL_STATUSES)
CLOSURE_REASONS = ("AUTOMATIC_SUPERSEDED",)


def _in(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
    ]


def _history_columns() -> list[sa.Column]:
    """Vigencia y metadatos D25 de un historial inmutable (solo se asigna `valid_to` una vez)."""
    return [
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(255), nullable=True),
    ]


def _history_checks(table: str) -> list[sa.CheckConstraint]:
    return [
        sa.CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name=op.f(f"ck_{table}_validity")),
        sa.CheckConstraint(
            "(valid_to IS NULL) = (closed_at IS NULL) AND (closed_at IS NULL) = (closed_by IS NULL)",
            name=op.f(f"ck_{table}_closure"),
        ),
    ]


HISTORY_GUARD = """
CREATE FUNCTION cr_pricing_history_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'El historial de % no se borra (spec 021)', TG_TABLE_NAME USING ERRCODE = 'check_violation';
    END IF;
    IF OLD.valid_to IS NOT NULL THEN
        RAISE EXCEPTION 'Un registro cerrado de % no cambia (spec 021)', TG_TABLE_NAME USING ERRCODE = 'check_violation';
    END IF;
    IF (to_jsonb(NEW) - ARRAY['valid_to', 'closed_at', 'closed_by'])
       IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['valid_to', 'closed_at', 'closed_by']) THEN
        RAISE EXCEPTION 'En % solo se puede cerrar la vigencia (spec 021)', TG_TABLE_NAME USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

APPLICATION_GUARD = f"""
CREATE FUNCTION cr_automatic_price_application_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Una aplicación automática de precio no se borra (spec 021)' USING ERRCODE = 'check_violation';
    END IF;
    IF OLD.status IN ({_in(FINAL_STATUSES)}) THEN
        RAISE EXCEPTION 'Una aplicación automática en estado final no cambia (RC-021-10)' USING ERRCODE = 'check_violation';
    END IF;
    IF (NEW.request_id, NEW.price_list_id, NEW.company_product_presentation_id, NEW.sequence, NEW.policy_id,
        NEW.term_id, NEW.markup_percentage, NEW.company_id)
       IS DISTINCT FROM
       (OLD.request_id, OLD.price_list_id, OLD.company_product_presentation_id, OLD.sequence, OLD.policy_id,
        OLD.term_id, OLD.markup_percentage, OLD.company_id) THEN
        RAISE EXCEPTION 'La captura de una aplicación automática es inmutable (RC-021-5)' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

REQUEST_GUARD = """
CREATE FUNCTION cr_automatic_price_request_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Una solicitud automática de precio es inmutable (spec 021)' USING ERRCODE = 'check_violation';
END;
$$;
"""


def upgrade() -> None:
    op.add_column(
        "company_products", sa.Column("purchase_tax_percentage", sa.Numeric(7, 4), nullable=True)
    )
    op.create_check_constraint(
        op.f("ck_company_products_purchase_tax_percentage_range"),
        "company_products",
        "purchase_tax_percentage IS NULL OR (purchase_tax_percentage >= 0 AND purchase_tax_percentage <= 100)",
    )

    op.create_table(
        POLICIES,
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("price_list_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivation_reason", sa.String(500), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["price_list_id", "company_id"],
            ["price_lists.id", "price_lists.company_id"],
            name="fk_price_list_pricing_policies_price_list",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("id", "price_list_id", name="uq_price_list_pricing_policies_id_price_list_id"),
        sa.CheckConstraint("status IN ('ACTIVE','INACTIVE')", name=op.f(f"ck_{POLICIES}_status")),
        sa.CheckConstraint(
            "(status = 'INACTIVE') = (deactivated_at IS NOT NULL)", name=op.f(f"ck_{POLICIES}_deactivation")
        ),
    )
    op.create_index(
        "uq_price_list_pricing_policies_name_ci",
        POLICIES,
        ["price_list_id", sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(op.f(f"ix_{POLICIES}_company_id_status"), POLICIES, ["company_id", "status"])

    op.create_table(
        TERMS,
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("policy_id", sa.UUID(), nullable=False),
        sa.Column("markup_percentage", sa.Numeric(8, 4), nullable=False),
        *_history_columns(),
        sa.ForeignKeyConstraint(
            ["policy_id"], [f"{POLICIES}.id"], name="fk_price_list_pricing_policy_terms_policy", ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "markup_percentage >= 0 AND markup_percentage <= 1000", name=op.f(f"ck_{TERMS}_markup_range")
        ),
        *_history_checks(TERMS),
    )
    op.execute(
        f"ALTER TABLE {TERMS} ADD CONSTRAINT ex_price_list_pricing_policy_terms_no_overlap "
        "EXCLUDE USING gist (policy_id WITH =, tstzrange(valid_from, valid_to, '[)') WITH &&)"
    )

    op.create_table(
        ASSIGNMENTS,
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("policy_id", sa.UUID(), nullable=False),
        sa.Column("price_list_id", sa.UUID(), nullable=False),
        sa.Column("company_product_presentation_id", sa.UUID(), nullable=False),
        *_history_columns(),
        sa.ForeignKeyConstraint(
            ["policy_id", "price_list_id"],
            [f"{POLICIES}.id", f"{POLICIES}.price_list_id"],
            name="fk_price_list_pricing_policy_presentations_policy",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_product_presentation_id", "company_id"],
            ["company_product_presentations.id", "company_product_presentations.company_id"],
            name="fk_price_list_pricing_policy_presentations_presentation",
            ondelete="RESTRICT",
        ),
        *_history_checks(ASSIGNMENTS),
    )
    op.execute(
        f"ALTER TABLE {ASSIGNMENTS} ADD CONSTRAINT ex_price_list_pricing_policy_presentations_no_overlap "
        "EXCLUDE USING gist (price_list_id WITH =, company_product_presentation_id WITH =, "
        "tstzrange(valid_from, valid_to, '[)') WITH &&)"
    )
    op.create_index(op.f(f"ix_{ASSIGNMENTS}_policy_id"), ASSIGNMENTS, ["policy_id"])

    op.create_table(
        REQUESTS,
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("contract_version", sa.SmallInteger(), nullable=False),
        sa.Column("purchase_id", sa.UUID(), nullable=False),
        sa.Column("purchase_detail_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("company_product_id", sa.UUID(), nullable=False),
        sa.Column("company_product_presentation_id", sa.UUID(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("previous_sequence", sa.Integer(), nullable=True),
        sa.Column("currency_code", sa.CHAR(3), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("previous_purchase_detail_id", sa.UUID(), nullable=True),
        sa.Column("previous_line_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("previous_quantity", sa.Numeric(18, 4), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_by_user_id", sa.UUID(), nullable=False),
        sa.Column("payload_hash", sa.CHAR(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_product_id", "company_id"],
            ["company_products.id", "company_products.company_id"],
            name="fk_automatic_price_update_requests_company_product",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["company_product_presentation_id", "company_product_id"],
            ["company_product_presentations.id", "company_product_presentations.company_product_id"],
            name="fk_automatic_price_update_requests_presentation",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("purchase_detail_id", name=op.f(f"uq_{REQUESTS}_purchase_detail_id")),
        sa.UniqueConstraint(
            "company_id", "company_product_presentation_id", "sequence", name="uq_automatic_price_update_requests_sequence"
        ),
        sa.CheckConstraint("sequence > 0", name=op.f(f"ck_{REQUESTS}_sequence_positive")),
        sa.CheckConstraint(
            "previous_sequence IS NULL OR previous_sequence = sequence - 1", name=op.f(f"ck_{REQUESTS}_previous_sequence")
        ),
        sa.CheckConstraint("quantity > 0", name=op.f(f"ck_{REQUESTS}_quantity_positive")),
        sa.CheckConstraint(
            "(previous_line_total IS NULL) = (previous_quantity IS NULL) "
            "AND (previous_quantity IS NULL OR previous_quantity > 0)",
            name=op.f(f"ck_{REQUESTS}_previous_facts"),
        ),
        sa.CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name=op.f(f"ck_{REQUESTS}_currency_code_format")),
    )

    op.create_table(
        APPLICATIONS,
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("price_list_id", sa.UUID(), nullable=False),
        sa.Column("company_product_presentation_id", sa.UUID(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("policy_id", sa.UUID(), nullable=True),
        sa.Column("term_id", sa.UUID(), nullable=True),
        sa.Column("markup_percentage", sa.Numeric(8, 4), nullable=True),
        sa.Column("current_unit_cost", sa.Numeric(28, 10), nullable=True),
        sa.Column("previous_unit_cost", sa.Numeric(28, 10), nullable=True),
        sa.Column("reference_cost", sa.Numeric(28, 10), nullable=True),
        sa.Column("previous_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("new_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("previous_price_item_id", sa.UUID(), nullable=True),
        sa.Column("new_price_item_id", sa.UUID(), nullable=True),
        sa.Column(
            "cancelled_future_item_ids",
            postgresql.ARRAY(sa.UUID()),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("first_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(60), nullable=True),
        sa.Column("last_error_detail", sa.String(500), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolution_reason", sa.String(500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(
            ["request_id"], [f"{REQUESTS}.id"], name="fk_automatic_price_applications_request", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["price_list_id", "company_id"],
            ["price_lists.id", "price_lists.company_id"],
            name="fk_automatic_price_applications_price_list",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], [f"{POLICIES}.id"], name="fk_automatic_price_applications_policy", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["term_id"], [f"{TERMS}.id"], name="fk_automatic_price_applications_term", ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("request_id", "price_list_id", name="uq_automatic_price_applications_request_list"),
        sa.CheckConstraint(f"status IN ({_in(STATUSES)})", name=op.f(f"ck_{APPLICATIONS}_status")),
        sa.CheckConstraint("attempts >= 0", name=op.f(f"ck_{APPLICATIONS}_attempts_non_negative")),
        sa.CheckConstraint(
            "(policy_id IS NULL) = (term_id IS NULL) AND (policy_id IS NULL) = (markup_percentage IS NULL)",
            name=op.f(f"ck_{APPLICATIONS}_capture"),
        ),
        sa.CheckConstraint(
            f"(status IN ({_in(FINAL_STATUSES)})) = (completed_at IS NOT NULL)",
            name=op.f(f"ck_{APPLICATIONS}_completion"),
        ),
        sa.CheckConstraint(
            "(status = 'RESOLVED') = (resolved_by IS NOT NULL AND resolution_reason IS NOT NULL)",
            name=op.f(f"ck_{APPLICATIONS}_resolution"),
        ),
    )
    op.create_index(
        "ix_automatic_price_applications_queue",
        APPLICATIONS,
        ["price_list_id", "company_product_presentation_id", "sequence"],
    )
    op.create_index(
        "ix_automatic_price_applications_pending",
        APPLICATIONS,
        ["next_attempt_at"],
        postgresql_where=sa.text("status IN ('PENDING', 'FAILED')"),
    )
    op.create_index(op.f(f"ix_{APPLICATIONS}_company_id_status"), APPLICATIONS, ["company_id", "status"])

    op.add_column("price_list_items", sa.Column("origin", sa.String(12), nullable=True))
    op.add_column("price_list_items", sa.Column("closure_reason", sa.String(30), nullable=True))
    op.add_column("price_list_items", sa.Column("automatic_application_id", sa.UUID(), nullable=True))
    op.create_check_constraint(
        op.f("ck_price_list_items_origin"), "price_list_items", "origin IS NULL OR origin = 'AUTOMATIC'"
    )
    op.create_check_constraint(
        op.f("ck_price_list_items_closure_reason"),
        "price_list_items",
        f"closure_reason IS NULL OR closure_reason IN ({_in(CLOSURE_REASONS)})",
    )
    op.create_foreign_key(
        "fk_price_list_items_automatic_application",
        "price_list_items",
        APPLICATIONS,
        ["automatic_application_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(HISTORY_GUARD)
    op.execute(APPLICATION_GUARD)
    op.execute(REQUEST_GUARD)
    for table in (TERMS, ASSIGNMENTS):
        op.execute(
            f"CREATE TRIGGER {table}_history BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION cr_pricing_history_guard()"
        )
    op.execute(
        f"CREATE TRIGGER {APPLICATIONS}_guard BEFORE UPDATE OR DELETE ON {APPLICATIONS} "
        "FOR EACH ROW EXECUTE FUNCTION cr_automatic_price_application_guard()"
    )
    op.execute(
        f"CREATE TRIGGER {REQUESTS}_immutable BEFORE UPDATE OR DELETE ON {REQUESTS} "
        "FOR EACH ROW EXECUTE FUNCTION cr_automatic_price_request_guard()"
    )


DOWNGRADE_GUARDS = (
    (f"SELECT count(*) FROM {POLICIES}", "políticas de precios"),
    (f"SELECT count(*) FROM {REQUESTS}", "solicitudes automáticas de precio"),
    ("SELECT count(*) FROM company_products WHERE purchase_tax_percentage IS NOT NULL", "tasas de impuesto de compra"),
    (
        "SELECT count(*) FROM price_list_items WHERE origin IS NOT NULL OR closure_reason IS NOT NULL",
        "precios creados o cerrados automáticamente",
    ),
)


def downgrade() -> None:
    connection = op.get_bind()
    for query, description in DOWNGRADE_GUARDS:
        count = connection.execute(sa.text(query)).scalar_one()
        if count:
            raise RuntimeError(
                f"El downgrade de la migración 0005 eliminaría {count} {description}. "
                "No se cambió nada: hace falta una decisión humana."
            )

    op.drop_constraint("fk_price_list_items_automatic_application", "price_list_items", type_="foreignkey")
    op.drop_constraint(op.f("ck_price_list_items_closure_reason"), "price_list_items", type_="check")
    op.drop_constraint(op.f("ck_price_list_items_origin"), "price_list_items", type_="check")
    op.drop_column("price_list_items", "automatic_application_id")
    op.drop_column("price_list_items", "closure_reason")
    op.drop_column("price_list_items", "origin")
    op.drop_table(APPLICATIONS)
    op.drop_table(REQUESTS)
    op.drop_table(ASSIGNMENTS)
    op.drop_table(TERMS)
    op.drop_table(POLICIES)
    op.execute("DROP FUNCTION cr_automatic_price_request_guard()")
    op.execute("DROP FUNCTION cr_automatic_price_application_guard()")
    op.execute("DROP FUNCTION cr_pricing_history_guard()")
    op.drop_constraint(
        op.f("ck_company_products_purchase_tax_percentage_range"), "company_products", type_="check"
    )
    op.drop_column("company_products", "purchase_tax_percentage")
