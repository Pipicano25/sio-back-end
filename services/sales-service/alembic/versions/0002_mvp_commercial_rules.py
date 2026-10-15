"""Reglas comerciales del MVP (spec 020): medio de pago declarado y ventas sin descuento.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-14

- `payment_method_id` y sus copias (FR-020-09, RC-MVP-4); obligatorio fuera de `DRAFT`.
- `ck_sale_details_no_discount` (FR-020-13, RC-MVP-6).
- `sale_sales_frozen()` se reemplaza para congelar las columnas nuevas.

Guarda (DS-09): se detiene sin cambios si hay líneas con descuento o ventas fuera de `DRAFT`
(no tendrían medio de pago). `downgrade` restaura la `0001`.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GUARDS = (
    ("SELECT count(*) FROM sale_details WHERE discount_amount <> 0", "líneas de venta con descuento"),
    ("SELECT count(*) FROM sales WHERE status <> 'DRAFT'", "ventas confirmadas o anuladas sin medio de pago"),
)
CHECKS = (
    ("sales", "ck_sales_payment_method_snapshot",
     "(payment_method_id IS NULL AND payment_method_code_snapshot IS NULL AND payment_method_name_snapshot IS NULL) "
     "OR (payment_method_id IS NOT NULL AND payment_method_code_snapshot IS NOT NULL "
     "AND payment_method_name_snapshot IS NOT NULL)"),
    ("sales", "ck_sales_payment_method_required", "status = 'DRAFT' OR payment_method_id IS NOT NULL"),
    ("sale_details", "ck_sale_details_no_discount", "discount_amount = 0"),
)

SALES_FROZEN = """
CREATE OR REPLACE FUNCTION sale_sales_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'DRAFT' THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'CANCELLED' OR NEW.status <> 'CANCELLED' THEN
        RAISE EXCEPTION 'La venta % en estado % no admite cambios.', OLD.id, OLD.status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (NEW.id, NEW.company_id, NEW.branch_id, NEW.company_customer_id, NEW.customer_payment_condition_id,
        NEW.payment_condition_code_snapshot, NEW.payment_terms_days_snapshot, NEW.due_date,
        NEW.sale_sequence_id, NEW.number, NEW.sequence_value, NEW.operation_date,
        NEW.customer_name_snapshot, NEW.customer_identification_snapshot, NEW.currency_code,
        NEW.observations, NEW.subtotal, NEW.discount_total, NEW.tax_total, NEW.total, NEW.has_unknown_cost,
        NEW.inventory_operation_id, NEW.payment_method_id, NEW.payment_method_code_snapshot,
        NEW.payment_method_name_snapshot, NEW.created_by_user_id, NEW.created_at, NEW.created_by)
       IS DISTINCT FROM
       (OLD.id, OLD.company_id, OLD.branch_id, OLD.company_customer_id, OLD.customer_payment_condition_id,
        OLD.payment_condition_code_snapshot, OLD.payment_terms_days_snapshot, OLD.due_date,
        OLD.sale_sequence_id, OLD.number, OLD.sequence_value, OLD.operation_date,
        OLD.customer_name_snapshot, OLD.customer_identification_snapshot, OLD.currency_code,
        OLD.observations, OLD.subtotal, OLD.discount_total, OLD.tax_total, OLD.total, OLD.has_unknown_cost,
        OLD.inventory_operation_id, OLD.payment_method_id, OLD.payment_method_code_snapshot,
        OLD.payment_method_name_snapshot, OLD.created_by_user_id, OLD.created_at, OLD.created_by) THEN
        RAISE EXCEPTION 'La venta confirmada % solo admite su anulación.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""
SALES_FROZEN_0001 = """
CREATE OR REPLACE FUNCTION sale_sales_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'DRAFT' THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'CANCELLED' OR NEW.status <> 'CANCELLED' THEN
        RAISE EXCEPTION 'La venta % en estado % no admite cambios.', OLD.id, OLD.status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (NEW.id, NEW.company_id, NEW.branch_id, NEW.company_customer_id, NEW.customer_payment_condition_id,
        NEW.payment_condition_code_snapshot, NEW.payment_terms_days_snapshot, NEW.due_date,
        NEW.sale_sequence_id, NEW.number, NEW.sequence_value, NEW.operation_date,
        NEW.customer_name_snapshot, NEW.customer_identification_snapshot, NEW.currency_code,
        NEW.observations, NEW.subtotal, NEW.discount_total, NEW.tax_total, NEW.total, NEW.has_unknown_cost,
        NEW.inventory_operation_id, NEW.created_by_user_id, NEW.created_at, NEW.created_by)
       IS DISTINCT FROM
       (OLD.id, OLD.company_id, OLD.branch_id, OLD.company_customer_id, OLD.customer_payment_condition_id,
        OLD.payment_condition_code_snapshot, OLD.payment_terms_days_snapshot, OLD.due_date,
        OLD.sale_sequence_id, OLD.number, OLD.sequence_value, OLD.operation_date,
        OLD.customer_name_snapshot, OLD.customer_identification_snapshot, OLD.currency_code,
        OLD.observations, OLD.subtotal, OLD.discount_total, OLD.tax_total, OLD.total, OLD.has_unknown_cost,
        OLD.inventory_operation_id, OLD.created_by_user_id, OLD.created_at, OLD.created_by) THEN
        RAISE EXCEPTION 'La venta confirmada % solo admite su anulación.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

def new_columns() -> list[sa.Column]:
    return [
        sa.Column("payment_method_id", sa.UUID(), nullable=True),
        sa.Column("payment_method_code_snapshot", sa.String(length=40), nullable=True),
        sa.Column("payment_method_name_snapshot", sa.String(length=120), nullable=True),
    ]


def upgrade() -> None:
    connection = op.get_bind()
    for query, description in GUARDS:
        count = connection.execute(sa.text(query)).scalar_one()
        if count:
            raise RuntimeError(
                f"La migración 0002 de Sales se detuvo sin cambios: hay {count} {description}. "
                "Hace falta una decisión humana antes de repetirla."
            )
    for column in new_columns():
        op.add_column("sales", column)
    for table, name, definition in CHECKS:
        op.create_check_constraint(op.f(name), table, definition)
    op.execute(SALES_FROZEN)


def downgrade() -> None:
    op.execute(SALES_FROZEN_0001)
    for table, name, _ in reversed(CHECKS):
        op.drop_constraint(op.f(name), table, type_="check")
    for column in reversed(new_columns()):
        op.drop_column("sales", column.name)
