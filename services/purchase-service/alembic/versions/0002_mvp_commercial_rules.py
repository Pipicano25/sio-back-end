"""Reglas comerciales del MVP (spec 020): recepción física, solo contado, medio de pago, presentación y costo > 0.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-14

- **Recepción** (FR-020-01..05, RC-MVP-1): la compra sigue `DRAFT`/`CONFIRMED`/`CANCELLED`; la
  recepción completa se expresa con `received_at`, `received_by_user_id` e `inventory_operation_id`
  (los tres juntos, una sola vez). Una compra `CONFIRMED` puede estar pendiente de recepción
  (sin entrada en Inventory). Nuevo tipo de operación `RECEIVE`.
- **Solo contado** (FR-020-08, RC-MVP-3): `ck_purchases_cash_only`.
- **Medio de pago** (FR-020-09, RC-MVP-4): `payment_method_id` y sus copias; obligatorio fuera de `DRAFT`.
- **Presentación y costo** (FR-020-11/12, RC-MVP-5): presentación obligatoria, `unit_cost > 0` y
  `discount_amount < subtotal`.
- `purchase_purchases_frozen()` se reemplaza: admite la recepción de una compra confirmada y congela
  las columnas nuevas.

**Guarda** (DS-09): si algún dato existente incumple las reglas nuevas, la migración se detiene **sin
cambios** (hace falta una decisión humana). `downgrade` restaura las definiciones de la `0001` y se
detiene si hay compras que el modelo anterior no puede representar.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GUARDS = (
    (
        "SELECT count(*) FROM purchases WHERE payment_condition_code_snapshot <> 'CASH' "
        "OR payment_terms_days_snapshot <> 0 OR due_date <> operation_date",
        "compras que no son de contado (CREDIT, FINANCING o con plazo)",
    ),
    (
        "SELECT count(*) FROM purchase_details WHERE company_product_presentation_id IS NULL",
        "líneas de compra sin presentación",
    ),
    (
        "SELECT count(*) FROM purchase_details WHERE unit_cost <= 0 OR discount_amount >= subtotal",
        "líneas de compra con costo unitario o costo neto no positivo",
    ),
    (
        "SELECT count(*) FROM purchase_operations WHERE operation_type = 'CONFIRM' AND status = 'PENDING'",
        "confirmaciones PENDING del modelo anterior (conciliarlas primero)",
    ),
    (
        "SELECT count(*) FROM purchases WHERE status <> 'DRAFT'",
        "compras confirmadas o anuladas sin medio de pago (el modelo nuevo lo exige fuera de DRAFT)",
    ),
)

DOWNGRADE_GUARDS = (
    (
        "SELECT count(*) FROM purchases WHERE status <> 'DRAFT' AND number IS NOT NULL AND inventory_operation_id IS NULL",
        "compras confirmadas o anuladas sin recepción (el modelo 0001 exige la entrada al confirmar)",
    ),
    (
        "SELECT count(*) FROM purchase_operations WHERE operation_type = 'RECEIVE'",
        "operaciones de recepción (no existen en el modelo 0001)",
    ),
)

LIFECYCLE = (
    "(status = 'DRAFT' AND number IS NULL AND sequence_value IS NULL AND purchase_sequence_id IS NULL "
    "AND inventory_operation_id IS NULL AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL "
    "AND cancellation_reason IS NULL) "
    "OR (status = 'CONFIRMED' AND number IS NOT NULL AND sequence_value IS NOT NULL AND purchase_sequence_id IS NOT NULL "
    "AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancellation_reason IS NULL) "
    "OR (status = 'CANCELLED' AND cancelled_by_user_id IS NOT NULL AND cancelled_at IS NOT NULL "
    "AND cancellation_reason IS NOT NULL AND ((number IS NULL AND sequence_value IS NULL AND purchase_sequence_id IS NULL "
    "AND inventory_operation_id IS NULL) OR (number IS NOT NULL AND sequence_value IS NOT NULL "
    "AND purchase_sequence_id IS NOT NULL)))"
)
LIFECYCLE_0001 = (
    "(status = 'DRAFT' AND number IS NULL AND sequence_value IS NULL AND purchase_sequence_id IS NULL AND inventory_operation_id IS NULL AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancellation_reason IS NULL) OR (status = 'CONFIRMED' AND number IS NOT NULL AND sequence_value IS NOT NULL AND purchase_sequence_id IS NOT NULL AND inventory_operation_id IS NOT NULL AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancellation_reason IS NULL) OR (status = 'CANCELLED' AND cancelled_by_user_id IS NOT NULL AND cancelled_at IS NOT NULL AND cancellation_reason IS NOT NULL AND ((number IS NULL AND sequence_value IS NULL AND purchase_sequence_id IS NULL AND inventory_operation_id IS NULL) OR (number IS NOT NULL AND sequence_value IS NOT NULL AND purchase_sequence_id IS NOT NULL AND inventory_operation_id IS NOT NULL)))"
)

NEW_CHECKS = (
    ("purchases", "ck_purchases_receipt",
     "(received_at IS NULL AND received_by_user_id IS NULL AND inventory_operation_id IS NULL) "
     "OR (received_at IS NOT NULL AND received_by_user_id IS NOT NULL AND inventory_operation_id IS NOT NULL)"),
    ("purchases", "ck_purchases_cash_only",
     "payment_condition_code_snapshot = 'CASH' AND payment_terms_days_snapshot = 0 AND due_date = operation_date"),
    ("purchases", "ck_purchases_payment_method_snapshot",
     "(payment_method_id IS NULL AND payment_method_code_snapshot IS NULL AND payment_method_name_snapshot IS NULL) "
     "OR (payment_method_id IS NOT NULL AND payment_method_code_snapshot IS NOT NULL "
     "AND payment_method_name_snapshot IS NOT NULL)"),
    ("purchases", "ck_purchases_payment_method_required", "status = 'DRAFT' OR payment_method_id IS NOT NULL"),
    ("purchase_details", "ck_purchase_details_presentation_required", "company_product_presentation_id IS NOT NULL"),
    ("purchase_details", "ck_purchase_details_net_cost", "discount_amount < subtotal"),
)
# (tabla, nombre, definición 0002, definición 0001)
REPLACED_CHECKS = (
    ("purchases", "ck_purchases_lifecycle", LIFECYCLE, LIFECYCLE_0001),
    ("purchase_details", "ck_purchase_details_unit_cost", "unit_cost > 0", "unit_cost >= 0"),
    ("purchase_operations", "ck_purchase_operations_operation_type",
     "operation_type IN ('CONFIRM','CANCEL','RECEIVE')", "operation_type IN ('CONFIRM','CANCEL')"),
    ("purchase_operations", "ck_purchase_operations_inventory_operation",
     "status <> 'SUCCEEDED' OR operation_type <> 'RECEIVE' OR inventory_operation_id IS NOT NULL",
     "status <> 'SUCCEEDED' OR operation_type = 'CANCEL' OR inventory_operation_id IS NOT NULL"),
)

PURCHASES_FROZEN = """
CREATE OR REPLACE FUNCTION purchase_purchases_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'DRAFT' THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'CANCELLED' OR NEW.status NOT IN ('CONFIRMED', 'CANCELLED') THEN
        RAISE EXCEPTION 'La compra % en estado % no admite cambios.', OLD.id, OLD.status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (NEW.id, NEW.company_id, NEW.branch_id, NEW.company_supplier_id, NEW.supplier_payment_condition_id,
        NEW.payment_condition_code_snapshot, NEW.payment_terms_days_snapshot, NEW.due_date,
        NEW.purchase_sequence_id, NEW.number, NEW.sequence_value, NEW.operation_date,
        NEW.promised_delivery_at, NEW.supplier_document_number, NEW.supplier_name_snapshot,
        NEW.supplier_identification_snapshot, NEW.currency_code, NEW.observations, NEW.subtotal,
        NEW.discount_total, NEW.tax_total, NEW.total, NEW.payment_method_id, NEW.payment_method_code_snapshot,
        NEW.payment_method_name_snapshot, NEW.created_by_user_id, NEW.created_at, NEW.created_by)
       IS DISTINCT FROM
       (OLD.id, OLD.company_id, OLD.branch_id, OLD.company_supplier_id, OLD.supplier_payment_condition_id,
        OLD.payment_condition_code_snapshot, OLD.payment_terms_days_snapshot, OLD.due_date,
        OLD.purchase_sequence_id, OLD.number, OLD.sequence_value, OLD.operation_date,
        OLD.promised_delivery_at, OLD.supplier_document_number, OLD.supplier_name_snapshot,
        OLD.supplier_identification_snapshot, OLD.currency_code, OLD.observations, OLD.subtotal,
        OLD.discount_total, OLD.tax_total, OLD.total, OLD.payment_method_id, OLD.payment_method_code_snapshot,
        OLD.payment_method_name_snapshot, OLD.created_by_user_id, OLD.created_at, OLD.created_by) THEN
        RAISE EXCEPTION 'La compra confirmada % solo admite su recepción o su anulación.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (OLD.inventory_operation_id IS NOT NULL OR NEW.status = 'CANCELLED')
       AND (NEW.inventory_operation_id, NEW.received_at, NEW.received_by_user_id)
           IS DISTINCT FROM (OLD.inventory_operation_id, OLD.received_at, OLD.received_by_user_id) THEN
        RAISE EXCEPTION 'La recepción de la compra % se registra una sola vez y no cambia.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

PURCHASES_FROZEN_0001 = """
CREATE OR REPLACE FUNCTION purchase_purchases_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'DRAFT' THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'CANCELLED' OR NEW.status <> 'CANCELLED' THEN
        RAISE EXCEPTION 'La compra % en estado % no admite cambios.', OLD.id, OLD.status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (NEW.id, NEW.company_id, NEW.branch_id, NEW.company_supplier_id, NEW.supplier_payment_condition_id,
        NEW.payment_condition_code_snapshot, NEW.payment_terms_days_snapshot, NEW.due_date,
        NEW.purchase_sequence_id, NEW.number, NEW.sequence_value, NEW.operation_date,
        NEW.promised_delivery_at, NEW.supplier_document_number, NEW.supplier_name_snapshot,
        NEW.supplier_identification_snapshot, NEW.currency_code, NEW.observations, NEW.subtotal,
        NEW.discount_total, NEW.tax_total, NEW.total, NEW.inventory_operation_id, NEW.created_by_user_id,
        NEW.created_at, NEW.created_by)
       IS DISTINCT FROM
       (OLD.id, OLD.company_id, OLD.branch_id, OLD.company_supplier_id, OLD.supplier_payment_condition_id,
        OLD.payment_condition_code_snapshot, OLD.payment_terms_days_snapshot, OLD.due_date,
        OLD.purchase_sequence_id, OLD.number, OLD.sequence_value, OLD.operation_date,
        OLD.promised_delivery_at, OLD.supplier_document_number, OLD.supplier_name_snapshot,
        OLD.supplier_identification_snapshot, OLD.currency_code, OLD.observations, OLD.subtotal,
        OLD.discount_total, OLD.tax_total, OLD.total, OLD.inventory_operation_id, OLD.created_by_user_id,
        OLD.created_at, OLD.created_by) THEN
        RAISE EXCEPTION 'La compra confirmada % solo admite su anulación.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

def new_columns() -> list[sa.Column]:
    """Columnas nuevas de `purchases` (anulables: los borradores existentes las completan al editarse)."""
    return [
        sa.Column("payment_method_id", sa.UUID(), nullable=True),
        sa.Column("payment_method_code_snapshot", sa.String(length=40), nullable=True),
        sa.Column("payment_method_name_snapshot", sa.String(length=120), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_by_user_id", sa.UUID(), nullable=True),
    ]


def _stop_if_any(guards) -> None:
    connection = op.get_bind()
    for query, description in guards:
        count = connection.execute(sa.text(query)).scalar_one()
        if count:
            raise RuntimeError(
                f"La migración 0002 de Purchase se detuvo sin cambios: hay {count} {description}. "
                "Hace falta una decisión humana antes de repetirla."
            )


def upgrade() -> None:
    _stop_if_any(GUARDS)
    for column in new_columns():
        op.add_column("purchases", column)
    for table, name, new, _ in REPLACED_CHECKS:
        op.drop_constraint(op.f(name), table, type_="check")
        op.create_check_constraint(op.f(name), table, new)
    for table, name, definition in NEW_CHECKS:
        op.create_check_constraint(op.f(name), table, definition)
    op.execute(PURCHASES_FROZEN)


def downgrade() -> None:
    _stop_if_any(DOWNGRADE_GUARDS)
    op.execute(PURCHASES_FROZEN_0001)
    for table, name, _ in reversed(NEW_CHECKS):
        op.drop_constraint(op.f(name), table, type_="check")
    for table, name, _, previous in REPLACED_CHECKS:
        op.drop_constraint(op.f(name), table, type_="check")
        op.create_check_constraint(op.f(name), table, previous)
    for column in reversed(new_columns()):
        op.drop_column("purchases", column.name)
